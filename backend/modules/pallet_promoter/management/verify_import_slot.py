"""
Script di VERIFICA e IMPORT Slot Merchandiser
Access → MSSQL

Uso:
    python verify_import_slot.py          # Solo verifica (default)
    python verify_import_slot.py --import # Verifica + Import

"""

import pyodbc
from datetime import datetime, date
import argparse

# ============================================
# CONFIGURAZIONE
# ============================================

ACCESS_FILE = r"C:\portale\backend\modules\pallet_promoter\management\Pallet_Promoter.accdb"

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

# ============================================
# VERIFICA SLOT ACCESS
# ============================================

def verify_access_slots(access_cur):
    """Analizza gli slot in Access e restituisce statistiche."""
    print("\n" + "=" * 60)
    print("📊 ANALISI SLOT IN ACCESS")
    print("=" * 60)
    
    # Conta totale
    access_cur.execute("SELECT COUNT(*) FROM T_Slot")
    total = access_cur.fetchone()[0]
    print(f"\n📦 Totale slot: {total}")
    
    # Slot con date valide
    access_cur.execute("""
        SELECT COUNT(*) FROM T_Slot 
        WHERE DataInizio IS NOT NULL AND DataFine IS NOT NULL
    """)
    valid = access_cur.fetchone()[0]
    print(f"✅ Slot con date valide: {valid}")
    print(f"⚠️  Slot senza date: {total - valid}")
    
    # Range date
    access_cur.execute("""
        SELECT MIN(DataInizio), MAX(DataFine) FROM T_Slot
        WHERE DataInizio IS NOT NULL AND DataFine IS NOT NULL
    """)
    row = access_cur.fetchone()
    if row[0] and row[1]:
        print(f"\n📅 Range date: {row[0].strftime('%d/%m/%Y')} → {row[1].strftime('%d/%m/%Y')}")
    
    # Slot per anno
    print("\n📆 Slot per anno:")
    access_cur.execute("""
        SELECT YEAR(DataInizio) as Anno, COUNT(*) as N
        FROM T_Slot
        WHERE DataInizio IS NOT NULL
        GROUP BY YEAR(DataInizio)
        ORDER BY YEAR(DataInizio)
    """)
    for row in access_cur.fetchall():
        print(f"   {row.Anno}: {row.N} slot")
    
    # Slot attivi (data_fine >= oggi)
    oggi = date.today()
    access_cur.execute(f"""
        SELECT COUNT(*) FROM T_Slot 
        WHERE DataFine >= #{oggi.strftime('%m/%d/%Y')}#
    """)
    attivi = access_cur.fetchone()[0]
    print(f"\n🟢 Slot attivi (fine >= oggi): {attivi}")
    
    # Slot futuri
    access_cur.execute(f"""
        SELECT COUNT(*) FROM T_Slot 
        WHERE DataInizio > #{oggi.strftime('%m/%d/%Y')}#
    """)
    futuri = access_cur.fetchone()[0]
    print(f"🔵 Slot futuri (inizio > oggi): {futuri}")
    
    # Distribuzione merchandiser
    print("\n👤 Slot per Merchandiser (top 15):")
    access_cur.execute("""
        SELECT TOP 15 
            T_Slot.codeMerchandiser, 
            T_Merchandiser.Cognome,
            T_Merchandiser.Nome,
            COUNT(*) as N
        FROM T_Slot
        LEFT JOIN T_Merchandiser ON T_Slot.codeMerchandiser = T_Merchandiser.ID
        WHERE T_Slot.DataInizio IS NOT NULL
        GROUP BY T_Slot.codeMerchandiser, T_Merchandiser.Cognome, T_Merchandiser.Nome
        ORDER BY COUNT(*) DESC
    """)
    for row in access_cur.fetchall():
        nome = f"{row.Cognome or ''} {row.Nome or ''}".strip() or "(senza nome)"
        print(f"   ID {row.codeMerchandiser}: {nome} → {row.N} slot")
    
    # Dettaglio slot anno corrente
    anno_corrente = oggi.year
    print(f"\n📋 Dettaglio slot {anno_corrente}:")
    access_cur.execute(f"""
        SELECT 
            T_Slot.ID,
            T_Merchandiser.Cognome,
            T_Merchandiser.Nome,
            T_Slot.DataInizio,
            T_Slot.DataFine,
            T_Slot.Lun, T_Slot.Mar, T_Slot.Mer, T_Slot.Gio, T_Slot.Ven, T_Slot.Sab, T_Slot.Dom,
            T_Slot.Note
        FROM T_Slot
        LEFT JOIN T_Merchandiser ON T_Slot.codeMerchandiser = T_Merchandiser.ID
        WHERE YEAR(T_Slot.DataInizio) = {anno_corrente}
           OR YEAR(T_Slot.DataFine) = {anno_corrente}
        ORDER BY T_Slot.DataInizio
    """)
    rows = access_cur.fetchall()
    
    print(f"   Trovati {len(rows)} slot per {anno_corrente}:\n")
    print(f"   {'ID':<5} {'Merchandiser':<25} {'Dal':<12} {'Al':<12} {'Giorni':<10} {'Note':<30}")
    print("   " + "-" * 100)
    
    for row in rows:
        nome = f"{row.Cognome or ''} {row.Nome or ''}".strip()[:24] or "(N/D)"
        data_inizio = row.DataInizio.strftime('%d/%m/%Y') if row.DataInizio else "N/D"
        data_fine = row.DataFine.strftime('%d/%m/%Y') if row.DataFine else "N/D"
        
        giorni = ""
        if row.Lun: giorni += "L"
        if row.Mar: giorni += "M"
        if row.Mer: giorni += "X"
        if row.Gio: giorni += "G"
        if row.Ven: giorni += "V"
        if row.Sab: giorni += "S"
        if row.Dom: giorni += "D"
        
        note = (row.Note or "")[:29]
        
        print(f"   {row.ID:<5} {nome:<25} {data_inizio:<12} {data_fine:<12} {giorni:<10} {note:<30}")
    
    return valid

# ============================================
# VERIFICA SLOT MSSQL
# ============================================

def verify_mssql_slots(mssql_cur):
    """Analizza gli slot già presenti in MSSQL."""
    print("\n" + "=" * 60)
    print("📊 ANALISI SLOT IN MSSQL (shared.slot)")
    print("=" * 60)
    
    mssql_cur.execute("SELECT COUNT(*) FROM shared.slot")
    total = mssql_cur.fetchone()[0]
    print(f"\n📦 Totale slot in MSSQL: {total}")
    
    if total > 0:
        mssql_cur.execute("SELECT MIN(data_inizio), MAX(data_fine) FROM shared.slot")
        row = mssql_cur.fetchone()
        if row[0] and row[1]:
            print(f"📅 Range date: {row[0].strftime('%d/%m/%Y')} → {row[1].strftime('%d/%m/%Y')}")
        
        # Slot per anno
        print("\n📆 Slot per anno:")
        mssql_cur.execute("""
            SELECT YEAR(data_inizio) as Anno, COUNT(*) as N
            FROM shared.slot
            GROUP BY YEAR(data_inizio)
            ORDER BY YEAR(data_inizio)
        """)
        for row in mssql_cur.fetchall():
            print(f"   {row.Anno}: {row.N} slot")
    
    return total

# ============================================
# IMPORT SLOT
# ============================================

def import_slots(access_cur, mssql_cur, mssql_conn):
    """Importa gli slot da Access a MSSQL."""
    print("\n" + "=" * 60)
    print("📥 IMPORT SLOT ACCESS → MSSQL")
    print("=" * 60)
    
    # Pulisci tabelle correlate prima
    print("\n🗑️  Pulizia tabelle esistenti...")
    mssql_cur.execute("DELETE FROM shared.slot_ingressi_uscite")
    mssql_cur.execute("DELETE FROM shared.slot_fornitori")
    mssql_cur.execute("DELETE FROM shared.slot")
    mssql_conn.commit()
    print("   ✅ Tabelle pulite")
    
    # Import T_Slot
    print("\n📦 T_Slot → shared.slot")
    access_cur.execute("""
        SELECT ID, codeMerchandiser, codeUtente, DataInizio, DataFine,
               Lun, Mar, Mer, Gio, Ven, Sab, Dom,
               Note, Docum, codeBadge, PlafondOre
        FROM T_Slot
        WHERE DataInizio IS NOT NULL AND DataFine IS NOT NULL
    """)
    rows = access_cur.fetchall()
    
    # Abilita IDENTITY_INSERT
    try:
        mssql_cur.execute("SET IDENTITY_INSERT shared.slot ON")
    except:
        pass
    
    count = 0
    errors = []
    for row in rows:
        try:
            mssql_cur.execute("""
                INSERT INTO shared.slot (id, merchandiser_id, utente_id, data_inizio, data_fine,
                                        lun, mar, mer, gio, ven, sab, dom,
                                        note, documento, badge, plafond_ore, attivo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
                row.ID, row.codeMerchandiser, row.codeUtente, row.DataInizio, row.DataFine,
                1 if row.Lun else 0, 1 if row.Mar else 0, 1 if row.Mer else 0,
                1 if row.Gio else 0, 1 if row.Ven else 0, 1 if row.Sab else 0, 1 if row.Dom else 0,
                row.Note, row.Docum, row.codeBadge, row.PlafondOre or 0
            )
            count += 1
        except Exception as e:
            errors.append(f"Slot {row.ID}: {e}")
    
    try:
        mssql_cur.execute("SET IDENTITY_INSERT shared.slot OFF")
    except:
        pass
    
    mssql_conn.commit()
    print(f"   ✅ {count} slot importati")
    
    if errors:
        print(f"   ⚠️  {len(errors)} errori:")
        for e in errors[:5]:
            print(f"      - {e}")
        if len(errors) > 5:
            print(f"      ... e altri {len(errors) - 5}")
    
    # Import T_FornitoriSlot
    print("\n📦 T_FornitoriSlot → shared.slot_fornitori")
    access_cur.execute("""
        SELECT codeSlot, codeAgenzia, codeFornitore, codeSRep, codeAttivita
        FROM T_FornitoriSlot
    """)
    rows = access_cur.fetchall()
    
    count_forn = 0
    for row in rows:
        try:
            mssql_cur.execute("""
                INSERT INTO shared.slot_fornitori (slot_id, agenzia_id, fornitore_id, sotto_reparto_id, attivita_id, buyer_id, note)
                VALUES (?, ?, ?, ?, ?, NULL, NULL)
            """,
                row.codeSlot, row.codeAgenzia or None, row.codeFornitore or None,
                row.codeSRep or None, row.codeAttivita or None
            )
            count_forn += 1
        except:
            pass
    
    mssql_conn.commit()
    print(f"   ✅ {count_forn} associazioni fornitore importate")
    
    # Import T_IngressiUscite_Polmone
    print("\n📦 T_IngressiUscite_Polmone → shared.slot_ingressi_uscite")
    access_cur.execute("""
        SELECT codeSlot, Data, Ing1, Usc1, Ing2, Usc2, IngExtra1, UscExtra1
        FROM T_IngressiUscite_Polmone
    """)
    rows = access_cur.fetchall()
    
    count_orari = 0
    for row in rows:
        try:
            mssql_cur.execute("""
                INSERT INTO shared.slot_ingressi_uscite (slot_id, data, ingresso_1, uscita_1, ingresso_2, uscita_2, ingresso_extra, uscita_extra, forzato, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
            """,
                row.codeSlot, row.Data,
                row.Ing1, row.Usc1, row.Ing2, row.Usc2, row.IngExtra1, row.UscExtra1
            )
            count_orari += 1
        except:
            pass
    
    mssql_conn.commit()
    print(f"   ✅ {count_orari} registrazioni orari importate")
    
    return count

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Verifica e importa slot merchandiser')
    parser.add_argument('--import', dest='do_import', action='store_true', 
                        help='Esegui import dopo verifica')
    parser.add_argument('--year', type=int, default=None,
                        help='Filtra per anno specifico (default: tutti)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("VERIFICA SLOT MERCHANDISER")
    print("Access → MSSQL")
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
    
    # Verifica Access
    access_count = verify_access_slots(access_cur)
    
    # Verifica MSSQL
    mssql_count = verify_mssql_slots(mssql_cur)
    
    # Riepilogo
    print("\n" + "=" * 60)
    print("📊 RIEPILOGO CONFRONTO")
    print("=" * 60)
    print(f"   Slot validi in Access: {access_count}")
    print(f"   Slot in MSSQL:         {mssql_count}")
    
    if access_count != mssql_count:
        print(f"   ⚠️  DIFFERENZA: {access_count - mssql_count} slot")
    else:
        print(f"   ✅ Nessuna differenza nel conteggio")
    
    # Import se richiesto
    if args.do_import:
        print("\n" + "=" * 60)
        confirm = input("🔴 Confermi l'import? Questo SOVRASCRIVERÀ i dati esistenti! (s/N): ")
        if confirm.lower() == 's':
            import_slots(access_cur, mssql_cur, mssql_conn)
            print("\n✅ IMPORT COMPLETATO!")
        else:
            print("\n❌ Import annullato")
    else:
        print("\n💡 Per importare, esegui: python verify_import_slot.py --import")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
