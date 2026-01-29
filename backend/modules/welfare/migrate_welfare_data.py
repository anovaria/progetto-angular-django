"""
-- Svuota tabelle welfare (ordine corretto per foreign key)
DELETE FROM welfare.dettaglio_buoni;
DELETE FROM welfare.richieste_provvisorie;
DELETE FROM welfare.email_importate;
DELETE FROM welfare.verifica_eudaimon;
DELETE FROM welfare.richieste;
DELETE FROM welfare.utenti;

-- Reset identity (opzionale, riparte da 1)
DBCC CHECKIDENT ('welfare.dettaglio_buoni', RESEED, 0);
DBCC CHECKIDENT ('welfare.richieste_provvisorie', RESEED, 0);
DBCC CHECKIDENT ('welfare.email_importate', RESEED, 0);
DBCC CHECKIDENT ('welfare.verifica_eudaimon', RESEED, 0);
DBCC CHECKIDENT ('welfare.richieste', RESEED, 0);
DBCC CHECKIDENT ('welfare.utenti', RESEED, 0);
------------------------------------------------------------------------
Script di migrazione dati da MS Access (wellfare_.accdb) a Django/MSSQL

LETTURA DIRETTA DA FILE .ACCDB via pyodbc

Uso:
    python modules\\welfare\\migrate_welfare_data.py C:\\path\\to\\wellfare_.accdb
    python modules\\welfare\\migrate_welfare_data.py C:\\path\\to\\wellfare_.accdb --dry-run
    python modules\\welfare\\migrate_welfare_data.py --init-only

Dalla shell Django:
    
    cd C:\inetpub\PortaleTest\django o C:\inetpub\PortaleIntranet\django  o C:\portale\backend
    python manage.py shell
    >>> from modules.welfare.migrate_welfare_data import migrate_from_access
    >>> migrate_from_access(r'C:\temp\wellfare.accdb', dry_run=True)
    >>> migrate_from_access(r'C:\wellfare.accdb') 

Prerequisiti:
    - pyodbc installato: pip install pyodbc
    - Microsoft Access Database Engine installato:
      https://www.microsoft.com/en-us/download/details.aspx?id=54920
      (Scarica "AccessDatabaseEngine_X64.exe" per Windows 64-bit)
"""

import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Setup Django se eseguito standalone
if __name__ == '__main__':
    # Cerca il path del progetto Django
    current = os.path.dirname(os.path.abspath(__file__))
    backend_path = os.path.abspath(os.path.join(current, '..', '..', '..'))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    # Prova diversi settings module in ordine
    settings_options = [
        'project_core.settings.dev',
        'project_core.settings.local', 
        'project_core.settings.prod',
        'project_core.settings',
    ]
    
    settings_found = False
    for settings_module in settings_options:
        try:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
            import django
            django.setup()
            settings_found = True
            print(f"Usando settings: {settings_module}")
            break
        except Exception as e:
            # Reset per provare il prossimo
            if 'django' in sys.modules:
                del sys.modules['django']
            os.environ.pop('DJANGO_SETTINGS_MODULE', None)
            continue
    
    if not settings_found:
        print("ERRORE: Impossibile trovare il modulo settings Django!")
        print("Prova a eseguire lo script dalla shell Django:")
        print("  python manage.py shell")
        print("  >>> from modules.welfare.migrate_welfare_data import migrate_from_access")
        print("  >>> migrate_from_access(r'C:\\path\\to\\file.accdb')")
        sys.exit(1)

from django.db import transaction
from django.utils import timezone


def get_access_connection(accdb_path):
    """
    Crea connessione al file Access.
    Prova diversi driver in ordine di preferenza.
    """
    import pyodbc
    
    # Lista driver Access in ordine di preferenza
    drivers = [
        'Microsoft Access Driver (*.mdb, *.accdb)',
        'Microsoft Access accdb Driver (*.mdb, *.accdb)',
        '{Microsoft Access Driver (*.mdb, *.accdb)}',
    ]
    
    # Trova driver disponibili
    available = [d for d in pyodbc.drivers() if 'Access' in d]
    print(f"Driver Access disponibili: {available}")
    
    # Prova i driver
    for driver in drivers + available:
        try:
            conn_str = f'DRIVER={{{driver}}};DBQ={accdb_path};'
            conn = pyodbc.connect(conn_str)
            print(f"Connesso con driver: {driver}")
            return conn
        except pyodbc.Error:
            continue
    
    raise Exception(
        "Nessun driver Access trovato!\n"
        "Installa Microsoft Access Database Engine:\n"
        "https://www.microsoft.com/en-us/download/details.aspx?id=54920"
    )


def parse_date(val):
    """Converte valore data Access in datetime timezone-aware."""
    if val is None:
        return None
    if isinstance(val, datetime):
        # Rendi timezone-aware se naive
        if val.tzinfo is None:
            from django.utils import timezone
            return timezone.make_aware(val)
        return val
    try:
        val_str = str(val).strip()
        if not val_str:
            return None
        for fmt in ['%m/%d/%y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', 
                    '%m/%d/%Y %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(val_str, fmt)
                # Rendi timezone-aware
                from django.utils import timezone
                return timezone.make_aware(dt)
            except ValueError:
                continue
        return None
    except:
        return None


def parse_decimal(val):
    """Converte valore in Decimal."""
    if val is None:
        return Decimal('0')
    try:
        if isinstance(val, (int, float)):
            return Decimal(str(val))
        val_str = str(val).replace('€', '').replace(' ', '').strip()
        val_str = val_str.replace(',', '.')
        return Decimal(val_str) if val_str else Decimal('0')
    except (InvalidOperation, ValueError):
        return Decimal('0')


def parse_int(val):
    """Converte valore in int."""
    if val is None:
        return 0
    try:
        if isinstance(val, int):
            return val
        return int(float(str(val).replace(',', '.').strip()))
    except (ValueError, TypeError):
        return 0


def clean_string(val, max_length=255):
    """Pulisce e tronca stringa."""
    if val is None:
        return ''
    return str(val).strip()[:max_length]


def migrate_from_access(accdb_path, dry_run=False):
    """
    Migra tutti i dati dal file Access al database Django.
    
    Args:
        accdb_path: Percorso completo al file .accdb
        dry_run: Se True, mostra solo cosa farebbe senza scrivere
    """
    from modules.welfare.models import (
        Ruolo, Utente, TaglioBuono, RichiestaWelfare,
        DettaglioBuono, RichiestaProvvisoria, EmailImportata,
        VerificaEudaimon
    )
    
    print("=" * 70)
    print("MIGRAZIONE DATI WELFARE DA MS ACCESS")
    print("=" * 70)
    print(f"File sorgente: {accdb_path}")
    print(f"Modalità: {'DRY RUN (nessuna scrittura)' if dry_run else 'ESECUZIONE REALE'}")
    print("=" * 70)
    
    if not os.path.exists(accdb_path):
        print(f"ERRORE: File non trovato: {accdb_path}")
        return False
    
    conn = get_access_connection(accdb_path)
    cursor = conn.cursor()
    
    try:
        with transaction.atomic():
            
            # ============================================================
            # 1. RUOLI
            # ============================================================
            print("\n[1/8] Migrazione T_Ruoli -> welfare_ruoli...")
            try:
                cursor.execute("SELECT ID_Ruolo, Descrizione FROM T_Ruoli")
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    if not dry_run:
                        Ruolo.objects.update_or_create(
                            id_ruolo=int(row.ID_Ruolo),
                            defaults={'descrizione': clean_string(row.Descrizione)}
                        )
                    count += 1
                print(f"   OK {count} ruoli")
            except Exception as e:
                print(f"   WARN Errore (creo default): {e}")
                if not dry_run:
                    for id_ruolo, desc in [(1, 'Front-Office'), (2, 'Ufficio Cassa'), 
                                           (3, 'Contabilità'), (99, 'Administrator')]:
                        Ruolo.objects.get_or_create(id_ruolo=id_ruolo, defaults={'descrizione': desc})
                print("   OK Ruoli default creati")
            
            # ============================================================
            # 2. TAGLI BUONO
            # ============================================================
            print("\n[2/8] Migrazione T_B_TMP -> welfare_tagli_buono...")
            try:
                cursor.execute("SELECT ValoreNominale FROM T_B_TMP WHERE ValoreNominale IS NOT NULL")
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    valore = parse_int(row.ValoreNominale)
                    if valore > 0:
                        if not dry_run:
                            TaglioBuono.objects.update_or_create(
                                valore_nominale=valore,
                                defaults={'attivo': True}
                            )
                        count += 1
                print(f"   OK {count} tagli")
            except Exception as e:
                print(f"   WARN Errore (creo default): {e}")
                if not dry_run:
                    for valore in [5, 10, 20, 25, 30, 50]:
                        TaglioBuono.objects.get_or_create(valore_nominale=valore, defaults={'attivo': True})
                print("   OK Tagli default creati")
            
            # ============================================================
            # 3. UTENTI
            # ============================================================
            print("\n[3/8] Migrazione T_Utenti -> welfare_utenti...")
            try:
                cursor.execute("SELECT Username, Ruolo, Dta_login, Volte FROM T_Utenti")
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    username = clean_string(row.Username, 255).lower()
                    if username:
                        ruolo_id = parse_int(row.Ruolo) or 1
                        if not dry_run:
                            try:
                                ruolo = Ruolo.objects.get(id_ruolo=ruolo_id)
                            except Ruolo.DoesNotExist:
                                ruolo = Ruolo.objects.get(id_ruolo=1)
                            
                            Utente.objects.update_or_create(
                                username=username,
                                defaults={
                                    'ruolo': ruolo,
                                    'data_login': parse_date(row.Dta_login),
                                    'volte': parse_int(row.Volte)
                                }
                            )
                        count += 1
                print(f"   OK {count} utenti")
            except Exception as e:
                print(f"   WARN Errore: {e}")
            
            # ============================================================
            # 4. RICHIESTE WELFARE (tabella principale)
            # ============================================================
            print("\n[4/8] Migrazione T_Wellfare -> welfare_richieste...")
            try:
                cursor.execute("""
                    SELECT ID, Data_Creazione, Data_Importazione, Data_Lavorazione,
                           Mittente, Nominativo, NomeMittente, Num_Richiesta,
                           ValoreBuono, QtaBuono, TotaleBuono, Stato,
                           Data_ConsegnaCliente, UtentePrep, UtenteCons,
                           Emettitore, Utente, controllo
                    FROM T_Wellfare
                    WHERE Num_Richiesta IS NOT NULL AND Num_Richiesta <> ''
                """)
                rows = cursor.fetchall()
                
                if not dry_run:
                    # Prepara lista per bulk_create, evitando duplicati
                    richieste_da_creare = []
                    num_richieste_visti = set()
                    duplicati = 0
                    
                    for row in rows:
                        num_richiesta = clean_string(row.Num_Richiesta, 50)
                        if not num_richiesta:
                            continue
                        
                        # Salta duplicati
                        if num_richiesta in num_richieste_visti:
                            duplicati += 1
                            continue
                        num_richieste_visti.add(num_richiesta)
                        
                        richieste_da_creare.append(RichiestaWelfare(
                            data_creazione=parse_date(row.Data_Creazione) or timezone.now(),
                            data_lavorazione=parse_date(row.Data_Lavorazione),
                            data_consegna=parse_date(row.Data_ConsegnaCliente),
                            mittente=clean_string(row.Mittente),
                            nome_mittente=clean_string(row.NomeMittente),
                            nominativo=clean_string(row.Nominativo),
                            emettitore=clean_string(row.Emettitore),
                            valore_buono=parse_decimal(row.ValoreBuono),
                            qta_buono=parse_int(row.QtaBuono),
                            totale_buono=parse_decimal(row.TotaleBuono),
                            stato=(clean_string(row.Stato) or 'PRONTO').upper(),
                            utente_preparazione=clean_string(row.UtentePrep, 30),
                            utente_consegna=clean_string(row.UtenteCons, 30),
                            controllo=float(row.controllo or 0),
                            num_richiesta=num_richiesta,
                        ))
                    
                    # Bulk insert (molto più veloce)
                    RichiestaWelfare.objects.bulk_create(richieste_da_creare, batch_size=500)
                    count = len(richieste_da_creare)
                    if duplicati > 0:
                        print(f"   WARN {duplicati} duplicati ignorati")
                else:
                    count = len(rows)
                
                print(f"   OK {count} richieste")
            except Exception as e:
                print(f"   ERROR Errore grave: {e}")
                import traceback
                traceback.print_exc()
            
            # ============================================================
            # 5. DETTAGLIO BUONI
            # ============================================================
            print("\n[5/8] Migrazione T_BuoniCadeau -> welfare_dettaglio_buoni...")
            try:
                cursor.execute("""
                    SELECT IDCadeau, Qtav, Taglio, Totv, Num_Richiesta 
                    FROM T_BuoniCadeau
                    WHERE Num_Richiesta IS NOT NULL AND Taglio > 0 AND Qtav > 0
                """)
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    num_richiesta = clean_string(row.Num_Richiesta, 50)
                    taglio_val = parse_int(row.Taglio)
                    qta = parse_int(row.Qtav)
                    
                    if not num_richiesta or taglio_val == 0 or qta == 0:
                        continue
                    
                    if not dry_run:
                        try:
                            richiesta = RichiestaWelfare.objects.get(num_richiesta=num_richiesta)
                            taglio = TaglioBuono.objects.get(valore_nominale=taglio_val)
                            
                            DettaglioBuono.objects.update_or_create(
                                richiesta=richiesta,
                                taglio=taglio,
                                defaults={
                                    'quantita': qta,
                                    'totale': Decimal(qta * taglio_val)
                                }
                            )
                            count += 1
                        except (RichiestaWelfare.DoesNotExist, TaglioBuono.DoesNotExist):
                            pass
                    else:
                        count += 1
                
                print(f"   OK {count} dettagli")
            except Exception as e:
                print(f"   WARN Errore: {e}")
            
            # ============================================================
            # 6. RICHIESTE PROVVISORIE
            # ============================================================
            print("\n[6/8] Migrazione T_WellfareProvv -> welfare_richieste_provvisorie...")
            try:
                cursor.execute("""
                    SELECT Data_Creazione, Data_Importazione, Data_Lavorazione,
                           Mittente, NomeMittente, Nominativo, Num_Richiesta,
                           ValoreBuono, QtaBuono, TotaleBuono, Stato,
                           Data_ConsegnaCliente, Emettitore
                    FROM T_WellfareProvv
                    WHERE Num_Richiesta IS NOT NULL
                """)
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    num_richiesta = clean_string(row.Num_Richiesta, 50)
                    if not num_richiesta:
                        continue
                    
                    if not dry_run:
                        RichiestaProvvisoria.objects.update_or_create(
                            num_richiesta=num_richiesta,
                            defaults={
                                'data_creazione': parse_date(row.Data_Creazione) or timezone.now(),
                                'data_lavorazione': parse_date(row.Data_Lavorazione),
                                'mittente': clean_string(row.Mittente),
                                'nome_mittente': clean_string(row.NomeMittente),
                                'nominativo': clean_string(row.Nominativo),
                                'valore_buono': clean_string(row.ValoreBuono),
                                'qta_buono': clean_string(row.QtaBuono),
                                'totale_buono': clean_string(row.TotaleBuono),
                                'stato': clean_string(row.Stato) or 'PRONTO',
                                'data_consegna': parse_date(row.Data_ConsegnaCliente),
                                'emettitore': clean_string(row.Emettitore),
                            }
                        )
                    count += 1
                print(f"   OK {count} provvisorie")
            except Exception as e:
                print(f"   WARN Errore: {e}")
            
            # ============================================================
            # 7. EMAIL IMPORTATE (solo ultime 100, può essere pesante)
            # ============================================================
            print("\n[7/8] Migrazione T_Email_importate -> welfare_email_importate...")
            try:
                cursor.execute("""
                    SELECT TOP 100 DataCreazione, SenderName, SenderAddress, 
                           [TO], CC, BCC, RicevutoIl, Oggetto, Categories, HTMLBody
                    FROM T_Email_importate
                    ORDER BY RicevutoIl DESC
                """)
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    if not dry_run:
                        EmailImportata.objects.create(
                            data_creazione=parse_date(row.DataCreazione) or timezone.now(),
                            sender_name=clean_string(row.SenderName),
                            sender_address=clean_string(row.SenderAddress),
                            destinatario=clean_string(row.TO),
                            cc=clean_string(row.CC),
                            bcc=clean_string(row.BCC),
                            ricevuto_il=parse_date(row.RicevutoIl) or timezone.now(),
                            oggetto=clean_string(row.Oggetto),
                            categorie=clean_string(row.Categories),
                            html_body=str(row.HTMLBody or '')[:50000],
                        )
                    count += 1
                print(f"   OK {count} email (ultime 100)")
            except Exception as e:
                print(f"   WARN Errore (skipped): {e}")
            
            # ============================================================
            # 8. VERIFICA EUDAIMON
            # ============================================================
            print("\n[8/8] Migrazione VerificaEudaimon -> welfare_verifica_eudaimon...")
            try:
                cursor.execute("""
                    SELECT [Numero richiesta], [Valore del buono], [Quantità],
                           Importo, [Nominativo dipendente], [Nome account],
                           Stato, [Data/ora apertura]
                    FROM VerificaEudaimon
                """)
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    if not dry_run:
                        VerificaEudaimon.objects.create(
                            numero_richiesta=clean_string(getattr(row, 'Numero richiesta', '')),
                            valore_buono=clean_string(getattr(row, 'Valore del buono', '')),
                            quantita=float(getattr(row, 'Quantità', 0) or 0),
                            importo=parse_decimal(row.Importo),
                            nominativo_dipendente=clean_string(getattr(row, 'Nominativo dipendente', '')),
                            nome_account=clean_string(getattr(row, 'Nome account', '')),
                            stato=clean_string(row.Stato),
                            data_ora_apertura=clean_string(getattr(row, 'Data/ora apertura', '')),
                        )
                    count += 1
                print(f"   OK {count} verifiche")
            except Exception as e:
                print(f"   WARN Errore: {e}")
            
            if dry_run:
                print("\n*** DRY RUN - Nessun dato scritto (rollback) ***")
                transaction.set_rollback(True)
    
    finally:
        cursor.close()
        conn.close()
    
    print("\n" + "=" * 70)
    print("MIGRAZIONE COMPLETATA!" if not dry_run else "DRY RUN COMPLETATO!")
    print("=" * 70)
    
    if not dry_run:
        from modules.welfare.models import Ruolo, Utente, TaglioBuono, RichiestaWelfare
        print(f"\nRiepilogo database Django:")
        print(f"  - Ruoli: {Ruolo.objects.count()}")
        print(f"  - Utenti: {Utente.objects.count()}")
        print(f"  - Tagli Buono: {TaglioBuono.objects.count()}")
        print(f"  - Richieste Welfare: {RichiestaWelfare.objects.count()}")
    
    return True


def create_initial_data():
    """Crea solo i dati iniziali (ruoli, tagli) senza migrazione."""
    from modules.welfare.models import Ruolo, TaglioBuono, Utente
    
    print("Creazione dati iniziali...")
    
    for id_ruolo, desc in [(1, 'Front-Office'), (2, 'Ufficio Cassa'), 
                           (3, 'Contabilità'), (99, 'Administrator')]:
        Ruolo.objects.get_or_create(id_ruolo=id_ruolo, defaults={'descrizione': desc})
    print("OK Ruoli creati")
    
    for valore in [5, 10, 20, 25, 30, 50]:
        TaglioBuono.objects.get_or_create(valore_nominale=valore, defaults={'attivo': True})
    print("OK Tagli creati")
    
    ruolo_admin = Ruolo.objects.get(id_ruolo=99)
    Utente.objects.get_or_create(username='admin', defaults={'ruolo': ruolo_admin})
    print("OK Utente admin creato")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migra dati Welfare da MS Access a Django/MSSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python migrate_welfare_data.py C:\\dati\\wellfare_.accdb
  python migrate_welfare_data.py C:\\dati\\wellfare_.accdb --dry-run
  python migrate_welfare_data.py --init-only
        """
    )
    parser.add_argument('accdb_path', nargs='?', help='Percorso al file .accdb')
    parser.add_argument('--dry-run', action='store_true', help='Simula senza scrivere dati')
    parser.add_argument('--init-only', action='store_true', help='Crea solo dati iniziali (ruoli, tagli)')
    
    args = parser.parse_args()
    
    if args.init_only:
        create_initial_data()
    elif args.accdb_path:
        migrate_from_access(args.accdb_path, dry_run=args.dry_run)
    else:
        parser.print_help()
        print("\nERRORE: Specifica il percorso al file .accdb o usa --init-only")
        sys.exit(1)
