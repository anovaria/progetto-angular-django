"""
Script di migrazione Assegnazioni Pallet e Testate

TScelte → shared.assegnazioni_pallet
TSceltaTestate → shared.assegnazioni_testate

Uso:
    python migrate_assegnazioni.py              # Solo verifica
    python migrate_assegnazioni.py --import    # Verifica + Import
"""

import pyodbc
from datetime import datetime
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

# ============================================
# VERIFICA
# ============================================

def verify_access(access_cur):
    """Analizza i dati in Access."""
    print("\n" + "=" * 60)
    print("📊 ANALISI ACCESS")
    print("=" * 60)
    
    # TScelte (Pallet)
    access_cur.execute("SELECT COUNT(*) FROM TScelte")
    count_scelte = access_cur.fetchone()[0]
    print(f"\n📦 TScelte (Pallet): {count_scelte} record")
    
    access_cur.execute("SELECT COUNT(*) FROM TScelte WHERE Fornitore IS NOT NULL AND Fornitore <> ''")
    con_fornitore = access_cur.fetchone()[0]
    print(f"   - Con fornitore assegnato: {con_fornitore}")
    
    access_cur.execute("SELECT MIN(NumPeriodo), MAX(NumPeriodo) FROM TScelte")
    row = access_cur.fetchone()
    print(f"   - Range periodi: {row[0]} → {row[1]}")
    
    # TSceltaTestateNew
    access_cur.execute("SELECT COUNT(*) FROM TSceltaTestateNew")
    count_testate = access_cur.fetchone()[0]
    print(f"\n📦 TSceltaTestateNew: {count_testate} record")
    
    access_cur.execute("SELECT COUNT(*) FROM TSceltaTestateNew WHERE CodeFornitore IS NOT NULL AND CodeFornitore <> 0")
    con_fornitore_t = access_cur.fetchone()[0]
    print(f"   - Con fornitore assegnato: {con_fornitore_t}")
    
    access_cur.execute("SELECT MIN(Anno), MAX(Anno) FROM TSceltaTestateNew")
    row = access_cur.fetchone()
    print(f"   - Range anni: {row[0]} → {row[1]}")
    
    return count_scelte, count_testate

def verify_mssql(mssql_cur):
    """Analizza i dati in MSSQL."""
    print("\n" + "=" * 60)
    print("📊 ANALISI MSSQL")
    print("=" * 60)
    
    try:
        mssql_cur.execute("SELECT COUNT(*) FROM shared.assegnazioni_pallet")
        count = mssql_cur.fetchone()[0]
        print(f"\n📦 shared.assegnazioni_pallet: {count} record")
    except Exception as e:
        print(f"\n📦 shared.assegnazioni_pallet: ERRORE - {e}")
    
    try:
        mssql_cur.execute("SELECT COUNT(*) FROM shared.assegnazioni_testate")
        count = mssql_cur.fetchone()[0]
        print(f"📦 shared.assegnazioni_testate: {count} record")
    except Exception as e:
        print(f"📦 shared.assegnazioni_testate: ERRORE - {e}")

# ============================================
# MAPPING
# ============================================

def build_pallet_map(mssql_cur):
    """Crea mapping codice pallet → id."""
    mssql_cur.execute("SELECT id, codice FROM shared.pallet")
    return {row[1]: row[0] for row in mssql_cur.fetchall()}

def build_testata_map(mssql_cur):
    """Crea mapping id testata."""
    mssql_cur.execute("SELECT id FROM shared.testate")
    return {row[0]: row[0] for row in mssql_cur.fetchall()}

def build_periodo_map(mssql_cur, access_cur):
    """Crea mapping IDPeriodo Access → id MSSQL basato su codice."""
    # Leggi periodi MSSQL con codice
    mssql_cur.execute("SELECT id, codice FROM shared.periodi")
    mssql_periodi = {}
    for row in mssql_cur.fetchall():
        id_mssql, codice = row
        if codice:
            # Rimuovi prefisso "P-" se presente
            codice_norm = codice.replace('P-', '').strip().upper()
            mssql_periodi[codice_norm] = id_mssql
    
    # Leggi periodi Access
    access_cur.execute("SELECT IDPeriodo, CodPromo FROM TPeriodiSellOut")
    mapping = {}
    for row in access_cur.fetchall():
        id_access, codice = row
        if codice:
            codice_norm = codice.strip().upper()
            if codice_norm in mssql_periodi:
                mapping[id_access] = mssql_periodi[codice_norm]
    
    return mapping

def build_fornitore_map_by_name(mssql_cur):
    """Crea mapping nome fornitore → codice (da shared.fornitori)."""
    mssql_cur.execute("SELECT codice, nome FROM shared.fornitori")
    mapping = {}
    for row in mssql_cur.fetchall():
        codice, nome = row
        if nome:
            # Normalizza il nome (uppercase, strip)
            nome_norm = nome.strip().upper()
            mapping[nome_norm] = codice
            # Anche una versione troncata a 30 caratteri
            if len(nome_norm) > 30:
                mapping[nome_norm[:30]] = codice
    return mapping

# ============================================
# IMPORT
# ============================================

def import_pallet(access_cur, mssql_cur, mssql_conn):
    """Importa TScelte → shared.assegnazioni_pallet."""
    print("\n📥 TScelte → shared.assegnazioni_pallet")
    
    # Mapping
    pallet_map = build_pallet_map(mssql_cur)
    periodo_map = build_periodo_map(mssql_cur, access_cur)
    fornitore_map = build_fornitore_map_by_name(mssql_cur)
    
    print(f"   Pallet trovati: {len(pallet_map)}")
    print(f"   Periodi trovati: {len(periodo_map)}")
    print(f"   Fornitori per nome: {len(fornitore_map)}")
    
    # Svuota tabella esistente
    print("   Pulizia tabella esistente...")
    mssql_cur.execute("DELETE FROM shared.assegnazioni_pallet")
    mssql_conn.commit()
    
    # Leggi da Access
    access_cur.execute("""
        SELECT ID, Fornitore, Dettaglio, Pallet, NumBuyer, NumPeriodo, Nota 
        FROM TScelte 
        ORDER BY NumPeriodo, Pallet
    """)
    
    count_inserted = 0
    count_skipped = 0
    count_no_fornitore = 0
    errors = 0
    
    for row in access_cur.fetchall():
        id_access, fornitore_nome, dettaglio, pallet_codice, num_buyer, num_periodo, nota = row
        
        # Verifica pallet esiste
        if pallet_codice not in pallet_map:
            count_skipped += 1
            continue
        
        # Verifica periodo esiste nel mapping
        if num_periodo not in periodo_map:
            count_skipped += 1
            continue
        
        periodo_id_mssql = periodo_map[num_periodo]
        
        # Cerca fornitore per nome
        fornitore_id = None
        if fornitore_nome:
            nome_norm = fornitore_nome.strip().upper()
            fornitore_id = fornitore_map.get(nome_norm)
            if not fornitore_id and len(nome_norm) > 30:
                fornitore_id = fornitore_map.get(nome_norm[:30])
            if not fornitore_id:
                count_no_fornitore += 1
        
        try:
            mssql_cur.execute("""
                INSERT INTO shared.assegnazioni_pallet 
                (periodo_id, pallet_id, fornitore_id, dettaglio)
                VALUES (?, ?, ?, ?)
            """,
                periodo_id_mssql, pallet_map[pallet_codice], fornitore_id, dettaglio
            )
            count_inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Errore: {e}")
    
    mssql_conn.commit()
    
    print(f"   ✅ {count_inserted} assegnazioni pallet importate")
    print(f"   ⏭️ {count_skipped} saltate (pallet/periodo non trovato)")
    print(f"   ❓ {count_no_fornitore} fornitori non trovati per nome")
    if errors > 5:
        print(f"   ⚠️ Altri {errors - 5} errori non mostrati")
    
    return count_inserted

def import_testate(access_cur, mssql_cur, mssql_conn):
    """Importa TSceltaTestateNew → shared.assegnazioni_testate."""
    print("\n📥 TSceltaTestateNew → shared.assegnazioni_testate")
    
    # Mapping
    testata_map = build_testata_map(mssql_cur)
    
    print(f"   Testate trovate: {len(testata_map)}")
    
    # Svuota tabella esistente
    print("   Pulizia tabella esistente...")
    mssql_cur.execute("DELETE FROM shared.assegnazioni_testate")
    mssql_conn.commit()
    
    # Leggi da Access - NOTA: usa TSceltaTestateNew
    access_cur.execute("""
        SELECT IDScelta, CodeMese, Anno, CodeFornitore, CodeTestata, NotaTestata, NotaAtelier
        FROM TSceltaTestateNew 
        ORDER BY Anno, CodeMese, CodeTestata
    """)
    
    count_inserted = 0
    count_skipped = 0
    errors = 0
    
    for row in access_cur.fetchall():
        id_access, mese, anno, code_fornitore, code_testata, nota_testata, nota_atelier = row
        
        # Verifica testata esiste
        if code_testata not in testata_map:
            count_skipped += 1
            continue
        
        # fornitore_id può essere None o 0
        fornitore_id = code_fornitore if code_fornitore and code_fornitore != 0 else None
        
        try:
            mssql_cur.execute("""
                INSERT INTO shared.assegnazioni_testate 
                (mese, anno, testata_id, fornitore_id, nota_testata, nota_atelier)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                mese, anno, code_testata, fornitore_id, nota_testata, nota_atelier
            )
            count_inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Errore: {e}")
    
    mssql_conn.commit()
    
    print(f"   ✅ {count_inserted} assegnazioni testate importate")
    print(f"   ⏭️ {count_skipped} saltate (testata non trovata)")
    if errors > 5:
        print(f"   ⚠️ Altri {errors - 5} errori non mostrati")
    
    return count_inserted

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Migra assegnazioni pallet e testate')
    parser.add_argument('--import', dest='do_import', action='store_true', 
                        help='Esegui import dopo verifica')
    args = parser.parse_args()
    
    print("=" * 60)
    print("MIGRAZIONE ASSEGNAZIONI PALLET E TESTATE")
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
        print("   1. CANCELLERÀ tutti i dati in shared.assegnazioni_pallet")
        print("   2. CANCELLERÀ tutti i dati in shared.assegnazioni_testate")
        print("   3. Importerà da Access")
        print("=" * 60)
        
        confirm = input("\n🔴 Confermi? (s/N): ")
        if confirm.lower() == 's':
            import_pallet(access_cur, mssql_cur, mssql_conn)
            import_testate(access_cur, mssql_cur, mssql_conn)
            
            print("\n" + "=" * 60)
            print("✅ IMPORT COMPLETATO!")
            print("=" * 60)
            
            # Verifica finale
            verify_mssql(mssql_cur)
        else:
            print("\n❌ Import annullato")
    else:
        print("\n💡 Per importare, esegui: python migrate_assegnazioni.py --import")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
