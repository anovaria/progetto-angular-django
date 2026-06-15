"""
Script di SYNC Presenze Hostess (INCREMENTALE)

THostessTask → shared.presenze_hostess

SYNC INCREMENTALE: aggiorna esistenti, inserisce nuovi, NON cancella nulla.

Uso:
    python sync_hostess_task.py              # Solo verifica
    python sync_hostess_task.py --sync       # Verifica + Sync incrementale
"""

import pyodbc
from datetime import datetime, time
import argparse

# ============================================
# CONFIGURAZIONE
# ============================================

ACCESS_FILE = r"C:\portale\django\modules\pallet_promoter\management\Pallet_Promoter.accdb"

MSSQL_SERVER = "srviisnew"
MSSQL_DATABASE = "DjangoIntranet"
MSSQL_DRIVER = "ODBC Driver 18 for SQL Server"
MSSQL_USER = "django_user"
MSSQL_PWD = "Sangiovese.2025@@"

# ============================================
# CONNESSIONI
# ============================================

def get_access_conn():
    conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ACCESS_FILE};'
    return pyodbc.connect(conn_str)

def get_mssql_conn():
    conn_str = (
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={MSSQL_DATABASE};"
        f"UID={MSSQL_USER};"
        f"PWD={MSSQL_PWD};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def parse_access_time(val):
    """Converte un valore time Access in time Python."""
    if val is None:
        return None
    if isinstance(val, time):
        if val.hour == 0 and val.minute == 0:
            return None
        return val
    if isinstance(val, datetime):
        if val.hour == 0 and val.minute == 0:
            return None
        return val.time()
    return None

# ============================================
# VERIFICA
# ============================================

def verify_access(access_cur):
    """Analizza i dati in Access."""
    print("\n" + "=" * 60)
    print("📊 ANALISI ACCESS - THostessTask")
    print("=" * 60)
    
    access_cur.execute("SELECT COUNT(*) FROM THostessTask")
    count = access_cur.fetchone()[0]
    print(f"\n📦 THostessTask: {count} giorni")
    
    access_cur.execute("SELECT MIN(Giorno), MAX(Giorno) FROM THostessTask WHERE Giorno IS NOT NULL")
    row = access_cur.fetchone()
    if row[0] and row[1]:
        print(f"   Range date: {row[0].strftime('%d/%m/%Y')} → {row[1].strftime('%d/%m/%Y')}")
    
    # Conta slot con hostess assegnate
    access_cur.execute("""
        SELECT COUNT(*) FROM THostessTask 
        WHERE CodeHostess1 IS NOT NULL OR CodeHostess2 IS NOT NULL 
           OR CodeHostess3 IS NOT NULL OR CodeHostess4 IS NOT NULL
    """)
    con_hostess = access_cur.fetchone()[0]
    print(f"   Giorni con almeno 1 hostess: {con_hostess}")
    
    return count

def verify_mssql(mssql_cur):
    """Analizza i dati in MSSQL."""
    print("\n" + "=" * 60)
    print("📊 ANALISI MSSQL")
    print("=" * 60)
    
    try:
        mssql_cur.execute("SELECT COUNT(*) FROM shared.presenze_hostess")
        count = mssql_cur.fetchone()[0]
        print(f"\n📦 shared.presenze_hostess: {count} record")
        
        mssql_cur.execute("SELECT COUNT(*) FROM shared.presenze_hostess WHERE hostess_id IS NOT NULL")
        con_hostess = mssql_cur.fetchone()[0]
        print(f"   - Con hostess assegnata: {con_hostess}")
    except Exception as e:
        print(f"\n📦 shared.presenze_hostess: ERRORE - {e}")

# ============================================
# SYNC INCREMENTALE
# ============================================

def sync_hostess_task(access_cur, mssql_cur, mssql_conn):
    """Sync THostessTask → shared.presenze_hostess (UPDATE o INSERT)."""
    print("\n🔄 SYNC THostessTask → shared.presenze_hostess")
    
    # Carica presenze esistenti in MSSQL
    mssql_cur.execute("""
        SELECT giorno, slot, hostess_id, agenzia_id, 
               ingresso_mattino, uscita_mattino, ingresso_pomeriggio, uscita_pomeriggio, nota
        FROM shared.presenze_hostess
    """)
    existing = {}
    for row in mssql_cur.fetchall():
        key = (row[0], row[1])  # (giorno, slot)
        existing[key] = {
            'hostess_id': row[2],
            'agenzia_id': row[3],
            'ingresso_mattino': row[4],
            'uscita_mattino': row[5],
            'ingresso_pomeriggio': row[6],
            'uscita_pomeriggio': row[7],
            'nota': row[8]
        }
    
    print(f"   Presenze esistenti MSSQL: {len(existing)}")
    
    # Leggi tutti i giorni da Access
    access_cur.execute("""
        SELECT * FROM THostessTask 
        WHERE Giorno IS NOT NULL
        ORDER BY Giorno
    """)
    
    count_inserted = 0
    count_updated = 0
    count_unchanged = 0
    count_days = 0
    errors = 0
    
    for row in access_cur.fetchall():
        count_days += 1
        giorno = row.Giorno
        
        if not isinstance(giorno, datetime):
            continue
        
        giorno_date = giorno.date() if isinstance(giorno, datetime) else giorno
        
        # Processa i 10 slot standard
        for slot_num in range(1, 11):
            suffix = str(slot_num) if slot_num <= 9 else 'X'
            
            hostess_id = getattr(row, f'CodeHostess{suffix}', None)
            agenzia_id = getattr(row, f'CodeAgency{slot_num}' if slot_num <= 10 else 'CodeAgency10', None)
            
            ing_matt = parse_access_time(getattr(row, f'IngressoMattino{suffix}', None))
            usc_matt = parse_access_time(getattr(row, f'UscitaMattino{suffix}', None))
            ing_pom = parse_access_time(getattr(row, f'IngressoPomeriggio{suffix}', None))
            usc_pom = parse_access_time(getattr(row, f'UscitaPomeriggio{suffix}', None))
            nota = getattr(row, f'Nota{suffix}', None)
            
            # Salta slot completamente vuoti
            if not hostess_id and not agenzia_id and not ing_matt and not usc_matt and not ing_pom and not usc_pom:
                continue
            
            key = (giorno_date, slot_num)
            
            try:
                if key in existing:
                    # Controlla se serve aggiornare
                    curr = existing[key]
                    if (curr['hostess_id'] != hostess_id or 
                        curr['agenzia_id'] != agenzia_id or
                        curr['ingresso_mattino'] != ing_matt or
                        curr['uscita_mattino'] != usc_matt or
                        curr['ingresso_pomeriggio'] != ing_pom or
                        curr['uscita_pomeriggio'] != usc_pom or
                        curr['nota'] != nota):
                        mssql_cur.execute("""
                            UPDATE shared.presenze_hostess 
                            SET hostess_id = ?, agenzia_id = ?,
                                ingresso_mattino = ?, uscita_mattino = ?,
                                ingresso_pomeriggio = ?, uscita_pomeriggio = ?, nota = ?
                            WHERE giorno = ? AND slot = ?
                        """, hostess_id, agenzia_id, ing_matt, usc_matt, ing_pom, usc_pom, nota, giorno_date, slot_num)
                        count_updated += 1
                    else:
                        count_unchanged += 1
                else:
                    # Inserisci nuovo
                    mssql_cur.execute("""
                        INSERT INTO shared.presenze_hostess 
                        (giorno, slot, tipo, hostess_id, agenzia_id, 
                         ingresso_mattino, uscita_mattino, ingresso_pomeriggio, uscita_pomeriggio, nota)
                        VALUES (?, ?, 'STD', ?, ?, ?, ?, ?, ?, ?)
                    """, giorno_date, slot_num, hostess_id, agenzia_id, ing_matt, usc_matt, ing_pom, usc_pom, nota)
                    count_inserted += 1
                    existing[key] = True
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ⚠️ Errore slot {slot_num} del {giorno_date}: {e}")
        
        # Processa i 5 slot Fabbrica (11-15)
        for fab_num in range(1, 6):
            slot_num = 10 + fab_num
            
            fornitore_id = getattr(row, f'CodeFornFab{fab_num}', None)
            hostess_id = getattr(row, f'CodeHostFab{fab_num}', None)
            agenzia_id = getattr(row, f'CodeAgeFab{fab_num}', None)
            
            ing_matt = parse_access_time(getattr(row, f'IngrMattFab{fab_num}', None))
            usc_matt = parse_access_time(getattr(row, f'UscMattFab{fab_num}', None))
            ing_pom = parse_access_time(getattr(row, f'IngrPomeFab{fab_num}', None))
            usc_pom = parse_access_time(getattr(row, f'UscPomeFab{fab_num}', None))
            nota = getattr(row, f'NotaFab{fab_num}', None)
            
            # Salta slot completamente vuoti
            if not hostess_id and not agenzia_id and not fornitore_id and not ing_matt and not usc_matt and not ing_pom and not usc_pom:
                continue
            
            key = (giorno_date, slot_num)
            
            try:
                if key in existing:
                    curr = existing[key]
                    if (curr['hostess_id'] != hostess_id or 
                        curr['agenzia_id'] != agenzia_id or
                        curr['ingresso_mattino'] != ing_matt or
                        curr['uscita_mattino'] != usc_matt or
                        curr['ingresso_pomeriggio'] != ing_pom or
                        curr['uscita_pomeriggio'] != usc_pom or
                        curr['nota'] != nota):
                        mssql_cur.execute("""
                            UPDATE shared.presenze_hostess 
                            SET hostess_id = ?, agenzia_id = ?, fornitore_id = ?,
                                ingresso_mattino = ?, uscita_mattino = ?,
                                ingresso_pomeriggio = ?, uscita_pomeriggio = ?, nota = ?
                            WHERE giorno = ? AND slot = ?
                        """, hostess_id, agenzia_id, fornitore_id, ing_matt, usc_matt, ing_pom, usc_pom, nota, giorno_date, slot_num)
                        count_updated += 1
                    else:
                        count_unchanged += 1
                else:
                    mssql_cur.execute("""
                        INSERT INTO shared.presenze_hostess 
                        (giorno, slot, tipo, hostess_id, agenzia_id, fornitore_id,
                         ingresso_mattino, uscita_mattino, ingresso_pomeriggio, uscita_pomeriggio, nota)
                        VALUES (?, ?, 'FAB', ?, ?, ?, ?, ?, ?, ?, ?)
                    """, giorno_date, slot_num, hostess_id, agenzia_id, fornitore_id, ing_matt, usc_matt, ing_pom, usc_pom, nota)
                    count_inserted += 1
                    existing[key] = True
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ⚠️ Errore slot FAB {slot_num} del {giorno_date}: {e}")
    
    mssql_conn.commit()
    
    print(f"   ✅ {count_inserted} nuove presenze inserite")
    print(f"   🔄 {count_updated} presenze aggiornate")
    print(f"   ⏸️ {count_unchanged} invariate")
    print(f"   📅 {count_days} giorni processati")
    if errors > 0:
        print(f"   ⚠️ {errors} errori")
    
    return count_inserted + count_updated

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Sync incrementale presenze hostess')
    parser.add_argument('--sync', dest='do_sync', action='store_true', 
                        help='Esegui sync incrementale')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SYNC INCREMENTALE PRESENZE HOSTESS")
    print("(Aggiorna esistenti, inserisce nuovi, NON cancella)")
    print("=" * 60)
    print(f"File Access: {ACCESS_FILE}")
    print(f"Database MSSQL: {MSSQL_DATABASE}")
    print(f"Data esecuzione: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    
    # Connessioni
    try:
        access_conn = get_access_conn()
        access_cur = access_conn.cursor()
        print("✅ Connesso a Access")
    except Exception as e:
        print(f"❌ Errore connessione Access: {e}")
        return
    
    try:
        mssql_conn = get_mssql_conn()
        mssql_cur = mssql_conn.cursor()
        print("✅ Connesso a MSSQL")
    except Exception as e:
        print(f"❌ Errore connessione MSSQL: {e}")
        return
    
    # Verifica
    verify_access(access_cur)
    verify_mssql(mssql_cur)
    
    # Sync
    if args.do_sync:
        print("\n" + "=" * 60)
        print("ℹ️  SYNC INCREMENTALE:")
        print("   - Aggiorna record esistenti se modificati")
        print("   - Inserisce nuovi record")
        print("   - NON cancella nulla")
        print("=" * 60)
        
        confirm = input("\n🟢 Confermi sync? (s/N): ")
        if confirm.lower() == 's':
            sync_hostess_task(access_cur, mssql_cur, mssql_conn)
            
            print("\n" + "=" * 60)
            print("✅ SYNC COMPLETATO!")
            print("=" * 60)
            
            # Verifica finale
            verify_mssql(mssql_cur)
        else:
            print("\n❌ Sync annullato")
    else:
        print("\n💡 Per sincronizzare, esegui: python sync_hostess_task.py --sync")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
