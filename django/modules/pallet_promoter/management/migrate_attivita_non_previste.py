"""
Script di migrazione CORRETTO
- Orari Merchandiser: T_IngressiUscite → shared.slot_ingressi_uscite
- Attività non previste: T_SlotPolmone + T_IngressiUscite_Polmone

Uso:
    python migrate_attivita_non_previste.py              # Solo verifica
    python migrate_attivita_non_previste.py --import    # Verifica + Import
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
        # Se è 00:00:00 consideralo come NULL
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
    print("📊 ANALISI ACCESS")
    print("=" * 60)
    
    # T_SlotPolmone (anagrafica nominativi)
    access_cur.execute("SELECT COUNT(*) FROM T_SlotPolmone")
    count_nominativi = access_cur.fetchone()[0]
    print(f"\n📦 T_SlotPolmone (nominativi): {count_nominativi} record")
    
    access_cur.execute("SELECT COUNT(*) FROM T_SlotPolmone WHERE DaEliminare = True")
    da_eliminare = access_cur.fetchone()[0]
    print(f"   - Da eliminare: {da_eliminare}")
    print(f"   - Attivi: {count_nominativi - da_eliminare}")
    
    # Esempi nominativi
    print("\n   Top 10 nominativi:")
    access_cur.execute("SELECT TOP 10 ID, Nominativo, Note FROM T_SlotPolmone ORDER BY Nominativo")
    for row in access_cur.fetchall():
        note = (row.Note or "")[:30]
        print(f"      {row.ID}: {row.Nominativo} - {note}")
    
    # T_IngressiUscite_Polmone (orari attività non previste)
    access_cur.execute("SELECT COUNT(*) FROM T_IngressiUscite_Polmone")
    count_orari_polmone = access_cur.fetchone()[0]
    print(f"\n📦 T_IngressiUscite_Polmone (orari att. non previste): {count_orari_polmone} record")
    
    access_cur.execute("SELECT MIN(Data), MAX(Data) FROM T_IngressiUscite_Polmone WHERE Data IS NOT NULL")
    row = access_cur.fetchone()
    if row[0] and row[1]:
        print(f"   Range date: {row[0].strftime('%d/%m/%Y')} → {row[1].strftime('%d/%m/%Y')}")
    
    # T_IngressiUscite (orari merchandiser - CORRETTI)
    access_cur.execute("SELECT COUNT(*) FROM T_IngressiUscite")
    count_orari_merch = access_cur.fetchone()[0]
    print(f"\n📦 T_IngressiUscite (orari merchandiser): {count_orari_merch} record")
    
    access_cur.execute("SELECT MIN(Data), MAX(Data) FROM T_IngressiUscite WHERE Data IS NOT NULL")
    row = access_cur.fetchone()
    if row[0] and row[1]:
        print(f"   Range date: {row[0].strftime('%d/%m/%Y')} → {row[1].strftime('%d/%m/%Y')}")
    
    return count_nominativi, count_orari_polmone, count_orari_merch

def verify_mssql(mssql_cur):
    """Analizza i dati in MSSQL."""
    print("\n" + "=" * 60)
    print("📊 ANALISI MSSQL")
    print("=" * 60)
    
    # slot_polmone
    try:
        mssql_cur.execute("SELECT COUNT(*) FROM shared.slot_polmone")
        count = mssql_cur.fetchone()[0]
        print(f"\n📦 shared.slot_polmone: {count} record")
    except:
        print(f"\n📦 shared.slot_polmone: TABELLA NON ESISTE")
    
    # ingressi_uscite_polmone
    try:
        mssql_cur.execute("SELECT COUNT(*) FROM shared.ingressi_uscite_polmone")
        count = mssql_cur.fetchone()[0]
        print(f"📦 shared.ingressi_uscite_polmone: {count} record")
    except:
        print(f"📦 shared.ingressi_uscite_polmone: TABELLA NON ESISTE")
    
    # slot_ingressi_uscite (merchandiser)
    try:
        mssql_cur.execute("SELECT COUNT(*) FROM shared.slot_ingressi_uscite")
        count = mssql_cur.fetchone()[0]
        print(f"📦 shared.slot_ingressi_uscite (merchandiser): {count} record")
    except:
        print(f"📦 shared.slot_ingressi_uscite: TABELLA NON ESISTE")

# ============================================
# IMPORT
# ============================================

def import_slot_polmone(access_cur, mssql_cur, mssql_conn):
    """Importa anagrafica nominativi."""
    print("\n📥 T_SlotPolmone → shared.slot_polmone")
    
    mssql_cur.execute("DELETE FROM shared.slot_polmone")
    
    access_cur.execute("SELECT ID, Nominativo, Note, DaEliminare FROM T_SlotPolmone")
    rows = access_cur.fetchall()
    
    count = 0
    for row in rows:
        try:
            mssql_cur.execute("""
                INSERT INTO shared.slot_polmone (id, nominativo, note, da_eliminare)
                VALUES (?, ?, ?, ?)
            """, row.ID, row.Nominativo, row.Note, 1 if row.DaEliminare else 0)
            count += 1
        except Exception as e:
            print(f"   ⚠️ Errore ID {row.ID}: {e}")
    
    mssql_conn.commit()
    print(f"   ✅ {count} nominativi importati")
    return count

def import_ingressi_uscite_polmone(access_cur, mssql_cur, mssql_conn):
    """Importa orari attività non previste."""
    print("\n📥 T_IngressiUscite_Polmone → shared.ingressi_uscite_polmone")
    
    mssql_cur.execute("DELETE FROM shared.ingressi_uscite_polmone")
    
    access_cur.execute("""
        SELECT codeSlot, Data, Ing1, Usc1, Ing2, Usc2, 
               IngExtra1, UscExtra1, IngExtra2, UscExtra2, forced
        FROM T_IngressiUscite_Polmone
        WHERE Data IS NOT NULL
    """)
    rows = access_cur.fetchall()
    
    count = 0
    errors = 0
    for row in rows:
        try:
            mssql_cur.execute("""
                INSERT INTO shared.ingressi_uscite_polmone 
                (slot_polmone_id, data, ingresso_1, uscita_1, ingresso_2, uscita_2,
                 ingresso_extra_1, uscita_extra_1, ingresso_extra_2, uscita_extra_2, forzato)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                row.codeSlot, row.Data,
                parse_access_time(row.Ing1), parse_access_time(row.Usc1),
                parse_access_time(row.Ing2), parse_access_time(row.Usc2),
                parse_access_time(row.IngExtra1), parse_access_time(row.UscExtra1),
                parse_access_time(row.IngExtra2), parse_access_time(row.UscExtra2),
                1 if row.forced else 0
            )
            count += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Errore slot {row.codeSlot}: {e}")
    
    mssql_conn.commit()
    print(f"   ✅ {count} orari importati")
    if errors > 5:
        print(f"   ⚠️ Altri {errors - 5} errori non mostrati")
    return count

def import_ingressi_uscite_merchandiser(access_cur, mssql_cur, mssql_conn):
    """Importa orari merchandiser dalla tabella CORRETTA."""
    print("\n📥 T_IngressiUscite → shared.slot_ingressi_uscite (CORREZIONE)")
    
    mssql_cur.execute("DELETE FROM shared.slot_ingressi_uscite")
    
    access_cur.execute("""
        SELECT codeSlot, Data, Ing1, Usc1, Ing2, Usc2, 
               IngExtra1, UscExtra1, forced
        FROM T_IngressiUscite
        WHERE Data IS NOT NULL
    """)
    rows = access_cur.fetchall()
    
    count = 0
    errors = 0
    for row in rows:
        try:
            mssql_cur.execute("""
                INSERT INTO shared.slot_ingressi_uscite 
                (slot_id, data, ingresso_1, uscita_1, ingresso_2, uscita_2,
                 ingresso_extra, uscita_extra, forzato, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
                row.codeSlot, row.Data,
                parse_access_time(row.Ing1), parse_access_time(row.Usc1),
                parse_access_time(row.Ing2), parse_access_time(row.Usc2),
                parse_access_time(row.IngExtra1), parse_access_time(row.UscExtra1),
                1 if row.forced else 0
            )
            count += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Errore slot {row.codeSlot}: {e}")
    
    mssql_conn.commit()
    print(f"   ✅ {count} orari merchandiser importati")
    if errors > 5:
        print(f"   ⚠️ Altri {errors - 5} errori non mostrati")
    return count

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Migra Attività non previste e corregge orari merchandiser')
    parser.add_argument('--import', dest='do_import', action='store_true', 
                        help='Esegui import dopo verifica')
    args = parser.parse_args()
    
    print("=" * 60)
    print("MIGRAZIONE ATTIVITÀ NON PREVISTE")
    print("+ CORREZIONE ORARI MERCHANDISER")
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
    count_nom, count_orari_polm, count_orari_merch = verify_access(access_cur)
    verify_mssql(mssql_cur)
    
    # Import
    if args.do_import:
        print("\n" + "=" * 60)
        print("⚠️  ATTENZIONE: Questo script:")
        print("   1. Importerà T_SlotPolmone → shared.slot_polmone")
        print("   2. Importerà T_IngressiUscite_Polmone → shared.ingressi_uscite_polmone")
        print("   3. CORREGGERÀ shared.slot_ingressi_uscite con T_IngressiUscite")
        print("=" * 60)
        
        confirm = input("\n🔴 Confermi? (s/N): ")
        if confirm.lower() == 's':
            # Disabilita FK
            print("\n⚙️  Disabilito vincoli FK...")
            try:
                mssql_cur.execute("ALTER TABLE shared.ingressi_uscite_polmone NOCHECK CONSTRAINT ALL")
            except:
                pass
            
            # Import
            import_slot_polmone(access_cur, mssql_cur, mssql_conn)
            import_ingressi_uscite_polmone(access_cur, mssql_cur, mssql_conn)
            import_ingressi_uscite_merchandiser(access_cur, mssql_cur, mssql_conn)
            
            # Riabilita FK
            print("\n⚙️  Riabilito vincoli FK...")
            try:
                mssql_cur.execute("ALTER TABLE shared.ingressi_uscite_polmone WITH CHECK CHECK CONSTRAINT ALL")
            except:
                pass
            
            print("\n" + "=" * 60)
            print("✅ IMPORT COMPLETATO!")
            print("=" * 60)
        else:
            print("\n❌ Import annullato")
    else:
        print("\n💡 Per importare, esegui: python migrate_attivita_non_previste.py --import")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
