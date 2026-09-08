"""
Script di migrazione THostessTask → shared.presenze_hostess

La tabella Access THostessTask ha una struttura "larga":
- 1 riga = 1 giorno
- Ogni riga contiene 10 slot standard + 5 slot fabbrica

Questo script "normalizza" i dati creando 1 riga per ogni slot.

Uso:
    python migrate_hostess_task.py              # Solo verifica
    python migrate_hostess_task.py --import    # Verifica + Import
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
    
    # Esempi recenti
    print("\n   Ultimi 5 giorni:")
    access_cur.execute("""
        SELECT TOP 5 Giorno, CodeHostess1, CodeHostess2, CodeHostess3, CodeHostess4
        FROM THostessTask 
        WHERE Giorno IS NOT NULL
        ORDER BY Giorno DESC
    """)
    for row in access_cur.fetchall():
        slots = [str(s) if s else '-' for s in [row.CodeHostess1, row.CodeHostess2, row.CodeHostess3, row.CodeHostess4]]
        print(f"      {row.Giorno.strftime('%d/%m/%Y')}: slot 1-4 = [{', '.join(slots)}]")
    
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
# IMPORT
# ============================================

def import_hostess_task(access_cur, mssql_cur, mssql_conn):
    """Importa THostessTask → shared.presenze_hostess."""
    print("\n📥 THostessTask → shared.presenze_hostess")
    
    # Svuota tabella esistente
    print("   Pulizia tabella esistente...")
    mssql_cur.execute("DELETE FROM shared.presenze_hostess")
    mssql_conn.commit()
    
    # Leggi tutti i giorni da Access
    access_cur.execute("""
        SELECT * FROM THostessTask 
        WHERE Giorno IS NOT NULL
        ORDER BY Giorno
    """)
    
    # Ottieni nomi colonne
    columns = [col[0] for col in access_cur.description]
    
    count_inserted = 0
    count_days = 0
    errors = 0
    
    for row in access_cur.fetchall():
        count_days += 1
        giorno = row.Giorno
        
        if not isinstance(giorno, datetime):
            continue
        
        giorno_date = giorno.date() if isinstance(giorno, datetime) else giorno
        
        # Processa i 10 slot standard (1-9 + X che diventa 10)
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
            
            try:
                mssql_cur.execute("""
                    INSERT INTO shared.presenze_hostess 
                    (giorno, slot, tipo, hostess_id, agenzia_id, 
                     ingresso_mattino, uscita_mattino, ingresso_pomeriggio, uscita_pomeriggio, nota)
                    VALUES (?, ?, 'STD', ?, ?, ?, ?, ?, ?, ?)
                """,
                    giorno_date, slot_num, hostess_id, agenzia_id,
                    ing_matt, usc_matt, ing_pom, usc_pom, nota
                )
                count_inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ⚠️ Errore slot {slot_num} del {giorno_date}: {e}")
        
        # Processa i 5 slot Fabbrica (11-15)
        for fab_num in range(1, 6):
            slot_num = 10 + fab_num  # Slot 11-15
            
            fornitore_id = getattr(row, f'CodeFornFab{fab_num}', None)
            hostess_id = getattr(row, f'CodeHostFab{fab_num}', None)
            agenzia_id = getattr(row, f'CodeAgeFab{fab_num}', None)
            
            ing_matt = parse_access_time(getattr(row, f'IngrMattFab{fab_num}', None))
            usc_matt = parse_access_time(getattr(row, f'UscMattFab{fab_num}', None))
            ing_pom = parse_access_time(getattr(row, f'IngrPomeFab{fab_num}', None))
            usc_pom = parse_access_time(getattr(row, f'UscPomeFab{fab_num}', None))
            nota = getattr(row, f'NotaFab{fab_num}', None)
            nota_forn = getattr(row, f'NotaFornFab{fab_num}', None)
            
            # Salta slot completamente vuoti
            if not hostess_id and not agenzia_id and not fornitore_id and not ing_matt and not usc_matt and not ing_pom and not usc_pom:
                continue
            
            try:
                mssql_cur.execute("""
                    INSERT INTO shared.presenze_hostess 
                    (giorno, slot, tipo, hostess_id, agenzia_id, fornitore_id,
                     ingresso_mattino, uscita_mattino, ingresso_pomeriggio, uscita_pomeriggio, 
                     nota, nota_fornitore)
                    VALUES (?, ?, 'FAB', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    giorno_date, slot_num, hostess_id, agenzia_id, fornitore_id,
                    ing_matt, usc_matt, ing_pom, usc_pom, nota, nota_forn
                )
                count_inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ⚠️ Errore slot FAB {slot_num} del {giorno_date}: {e}")
    
    mssql_conn.commit()
    
    print(f"   ✅ {count_inserted} presenze importate da {count_days} giorni")
    if errors > 5:
        print(f"   ⚠️ Altri {errors - 5} errori non mostrati")
    
    return count_inserted

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Migra THostessTask a shared.presenze_hostess')
    parser.add_argument('--import', dest='do_import', action='store_true', 
                        help='Esegui import dopo verifica')
    args = parser.parse_args()
    
    print("=" * 60)
    print("MIGRAZIONE HOSTESS TASK")
    print("THostessTask → shared.presenze_hostess")
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
    
    # Import
    if args.do_import:
        print("\n" + "=" * 60)
        print("⚠️  ATTENZIONE: Questo script:")
        print("   1. CANCELLERÀ tutti i dati in shared.presenze_hostess")
        print("   2. Importerà THostessTask normalizzando i 15 slot")
        print("=" * 60)
        
        confirm = input("\n🔴 Confermi? (s/N): ")
        if confirm.lower() == 's':
            import_hostess_task(access_cur, mssql_cur, mssql_conn)
            
            print("\n" + "=" * 60)
            print("✅ IMPORT COMPLETATO!")
            print("=" * 60)
            
            # Verifica finale
            verify_mssql(mssql_cur)
        else:
            print("\n❌ Import annullato")
    else:
        print("\n💡 Per importare, esegui: python migrate_hostess_task.py --import")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
