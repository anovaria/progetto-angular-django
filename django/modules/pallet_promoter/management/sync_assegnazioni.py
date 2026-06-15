"""
Script di SYNC Assegnazioni Pallet e Testate (INCREMENTALE)

TScelte → shared.assegnazioni_pallet
TSceltaTestateNew → shared.assegnazioni_testate

SYNC INCREMENTALE: aggiorna esistenti, inserisce nuovi, NON cancella nulla.

Uso:
    python sync_assegnazioni.py              # Solo verifica
    python sync_assegnazioni.py --sync       # Verifica + Sync incrementale
"""

import pyodbc
from datetime import datetime
import argparse

# ============================================
# CONFIGURAZIONE
# ============================================

ACCESS_FILE = r"C:\portale\django\modules\pallet_promoter\management\Pallet_Promoter.accdb"

MSSQL_SERVER = "srviisnew"
MSSQL_DATABASE_PROD = "DjangoIntranet"
MSSQL_DATABASE_TEST = "DjangoIntranet-test"
MSSQL_DATABASE_GOLD = "Db_GoldReport"
MSSQL_DRIVER = "ODBC Driver 18 for SQL Server"
MSSQL_USER = "django_user"
MSSQL_PWD = "Sangiovese.2025@@"

# ============================================
# CONNESSIONI
# ============================================

def get_access_conn():
    conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ACCESS_FILE};'
    return pyodbc.connect(conn_str)

def get_gold_conn():
    conn_str = (
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={MSSQL_DATABASE_GOLD};"
        f"UID={MSSQL_USER};"
        f"PWD={MSSQL_PWD};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def get_mssql_conn(test=False):
    db = MSSQL_DATABASE_TEST if test else MSSQL_DATABASE_PROD
    conn_str = (
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={db};"
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
    mssql_cur.execute("SELECT id, codice FROM shared.periodi")
    mssql_periodi = {}
    for row in mssql_cur.fetchall():
        id_mssql, codice = row
        if codice:
            codice_norm = codice.replace('P-', '').strip().upper()
            mssql_periodi[codice_norm] = id_mssql
    
    access_cur.execute("SELECT IDPeriodo, CodPromo FROM TPeriodiSellOut")
    mapping = {}
    for row in access_cur.fetchall():
        id_access, codice = row
        if codice:
            codice_norm = codice.strip().upper()
            if codice_norm in mssql_periodi:
                mapping[id_access] = mssql_periodi[codice_norm]
    
    return mapping

def build_fornitore_map_by_name(gold_cur):
    """Crea mapping nome fornitore → codice (da GoldReport.TFornitori)."""
    gold_cur.execute("SELECT FCODFO, FNOMFO FROM TFornitori WHERE FNOMFO IS NOT NULL")
    mapping = {}
    for row in gold_cur.fetchall():
        codice, nome = row
        if nome:
            nome_norm = nome.strip().upper()
            mapping[nome_norm] = codice
            if len(nome_norm) > 30:
                mapping[nome_norm[:30]] = codice
    return mapping

# ============================================
# SYNC INCREMENTALE
# ============================================

def sync_pallet(access_cur, mssql_cur, mssql_conn, gold_cur, dry_run=False):
    """Sync TScelte → shared.assegnazioni_pallet (UPDATE o INSERT)."""
    label = "[DRY-RUN] " if dry_run else ""
    print(f"\n🔄 {label}SYNC TScelte → shared.assegnazioni_pallet")

    # Mapping
    pallet_map = build_pallet_map(mssql_cur)
    periodo_map = build_periodo_map(mssql_cur, access_cur)
    fornitore_map = build_fornitore_map_by_name(gold_cur)
    
    print(f"   Pallet trovati: {len(pallet_map)}")
    print(f"   Periodi trovati: {len(periodo_map)}")
    print(f"   Fornitori per nome: {len(fornitore_map)}")
    
    # Carica assegnazioni esistenti in MSSQL
    mssql_cur.execute("SELECT periodo_id, pallet_id, fornitore_id, dettaglio FROM shared.assegnazioni_pallet")
    existing = {}
    for row in mssql_cur.fetchall():
        key = (row[0], row[1])  # (periodo_id, pallet_id)
        existing[key] = {'fornitore_id': row[2], 'dettaglio': row[3]}
    
    print(f"   Assegnazioni esistenti MSSQL: {len(existing)}")
    
    # Leggi da Access
    access_cur.execute("""
        SELECT ID, Fornitore, Dettaglio, Pallet, NumBuyer, NumPeriodo, Nota 
        FROM TScelte 
        ORDER BY NumPeriodo, Pallet
    """)
    
    count_inserted = 0
    count_updated = 0
    count_skipped = 0
    count_unchanged = 0
    errors = 0
    
    for row in access_cur.fetchall():
        id_access, fornitore_nome, dettaglio, pallet_codice, num_buyer, num_periodo, nota = row
        
        # Verifica pallet esiste
        if pallet_codice not in pallet_map:
            count_skipped += 1
            continue
        
        # Verifica periodo esiste
        if num_periodo not in periodo_map:
            count_skipped += 1
            continue
        
        periodo_id_mssql = periodo_map[num_periodo]
        pallet_id = pallet_map[pallet_codice]
        
        # Cerca fornitore per nome
        fornitore_id = None
        if fornitore_nome:
            nome_norm = fornitore_nome.strip().upper()
            fornitore_id = fornitore_map.get(nome_norm)
            if not fornitore_id and len(nome_norm) > 30:
                fornitore_id = fornitore_map.get(nome_norm[:30])
        
        key = (periodo_id_mssql, pallet_id)
        
        try:
            if key in existing:
                curr = existing[key]
                if curr['fornitore_id'] != fornitore_id or curr['dettaglio'] != dettaglio:
                    if not dry_run:
                        mssql_cur.execute("""
                            UPDATE shared.assegnazioni_pallet
                            SET fornitore_id = ?, dettaglio = ?
                            WHERE periodo_id = ? AND pallet_id = ?
                        """, fornitore_id, dettaglio, periodo_id_mssql, pallet_id)
                    count_updated += 1
                else:
                    count_unchanged += 1
            else:
                if not dry_run:
                    mssql_cur.execute("""
                        INSERT INTO shared.assegnazioni_pallet
                        (periodo_id, pallet_id, fornitore_id, dettaglio)
                        VALUES (?, ?, ?, ?)
                    """, periodo_id_mssql, pallet_id, fornitore_id, dettaglio)
                count_inserted += 1
                existing[key] = True
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Errore: {e}")

    if not dry_run:
        mssql_conn.commit()
    
    print(f"   ✅ {count_inserted} nuove assegnazioni {'da inserire' if dry_run else 'inserite'}")
    print(f"   🔄 {count_updated} assegnazioni {'da aggiornare' if dry_run else 'aggiornate'}")
    print(f"   ⏸️ {count_unchanged} invariate")
    print(f"   ⏭️ {count_skipped} saltate (pallet/periodo non trovato)")
    if errors > 0:
        print(f"   ⚠️ {errors} errori")

    return count_inserted + count_updated

def sync_testate(access_cur, mssql_cur, mssql_conn, dry_run=False):
    """Sync TSceltaTestateNew → shared.assegnazioni_testate (UPDATE o INSERT)."""
    label = "[DRY-RUN] " if dry_run else ""
    print(f"\n🔄 {label}SYNC TSceltaTestateNew → shared.assegnazioni_testate")
    
    # Mapping
    testata_map = build_testata_map(mssql_cur)
    print(f"   Testate trovate: {len(testata_map)}")
    
    # Carica assegnazioni esistenti in MSSQL
    mssql_cur.execute("SELECT mese, anno, testata_id, fornitore_id, nota_testata, nota_atelier FROM shared.assegnazioni_testate")
    existing = {}
    for row in mssql_cur.fetchall():
        key = (row[0], row[1], row[2])  # (mese, anno, testata_id)
        existing[key] = {'fornitore_id': row[3], 'nota_testata': row[4], 'nota_atelier': row[5]}
    
    print(f"   Assegnazioni esistenti MSSQL: {len(existing)}")
    
    # Leggi da Access
    access_cur.execute("""
        SELECT IDScelta, CodeMese, Anno, CodeFornitore, CodeTestata, NotaTestata, NotaAtelier
        FROM TSceltaTestateNew 
        ORDER BY Anno, CodeMese, CodeTestata
    """)
    
    count_inserted = 0
    count_updated = 0
    count_skipped = 0
    count_unchanged = 0
    errors = 0
    
    for row in access_cur.fetchall():
        id_access, mese, anno, code_fornitore, code_testata, nota_testata, nota_atelier = row
        
        # Verifica testata esiste
        if code_testata not in testata_map:
            count_skipped += 1
            continue
        
        fornitore_id = code_fornitore if code_fornitore and code_fornitore != 0 else None
        
        key = (mese, anno, code_testata)
        
        try:
            if key in existing:
                curr = existing[key]
                if (curr['fornitore_id'] != fornitore_id or
                    curr['nota_testata'] != nota_testata or
                    curr['nota_atelier'] != nota_atelier):
                    if not dry_run:
                        mssql_cur.execute("""
                            UPDATE shared.assegnazioni_testate
                            SET fornitore_id = ?, nota_testata = ?, nota_atelier = ?
                            WHERE mese = ? AND anno = ? AND testata_id = ?
                        """, fornitore_id, nota_testata, nota_atelier, mese, anno, code_testata)
                    count_updated += 1
                else:
                    count_unchanged += 1
            else:
                if not dry_run:
                    mssql_cur.execute("""
                        INSERT INTO shared.assegnazioni_testate
                        (mese, anno, testata_id, fornitore_id, nota_testata, nota_atelier)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, mese, anno, code_testata, fornitore_id, nota_testata, nota_atelier)
                count_inserted += 1
                existing[key] = True
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Errore: {e}")
    
    if not dry_run:
        mssql_conn.commit()

    print(f"   ✅ {count_inserted} nuove assegnazioni {'da inserire' if dry_run else 'inserite'}")
    print(f"   🔄 {count_updated} assegnazioni {'da aggiornare' if dry_run else 'aggiornate'}")
    print(f"   ⏸️ {count_unchanged} invariate")
    print(f"   ⏭️ {count_skipped} saltate (testata non trovata)")
    if errors > 0:
        print(f"   ⚠️ {errors} errori")

    return count_inserted + count_updated

# ============================================
# SYNC BUYER PALLET
# ============================================

def sync_buyer_pallet(access_cur, mssql_cur, mssql_conn):
    """Sync TPallet.NumBuyer → shared.pallet.buyer_id."""
    print("\n🔄 SYNC TPallet.NumBuyer → shared.pallet.buyer_id")

    # Mapping prefissi Access → MSSQL (quando il codice pallet è stato rinominato)
    PREFIX_MAP = {
        'LA': 'GL',  # Loredana (LA in Access → GL in MSSQL)
    }

    def normalizza_codice(codice):
        for old, new in PREFIX_MAP.items():
            if codice.startswith(old):
                return new + codice[len(old):]
        return codice

    # Leggi pallet da Access: codice normalizzato → num_buyer
    access_cur.execute("SELECT Descrizione, NumBuyer FROM TPallet")
    access_pallet = {normalizza_codice(row[0]): row[1] for row in access_cur.fetchall()}
    print(f"   Pallet in Access: {len(access_pallet)}")

    # Leggi pallet da MSSQL: codice → (id, buyer_id attuale)
    mssql_cur.execute("SELECT id, codice, buyer_id FROM shared.pallet")
    mssql_pallet = {row[1]: {'id': row[0], 'buyer_id': row[2]} for row in mssql_cur.fetchall()}
    print(f"   Pallet in MSSQL: {len(mssql_pallet)}")

    count_updated = 0
    count_unchanged = 0
    count_skipped = 0
    errors = 0

    for codice, num_buyer in access_pallet.items():
        if codice not in mssql_pallet:
            count_skipped += 1
            continue

        curr = mssql_pallet[codice]
        if curr['buyer_id'] == num_buyer:
            count_unchanged += 1
            continue

        try:
            mssql_cur.execute(
                "UPDATE shared.pallet SET buyer_id = ? WHERE id = ?",
                num_buyer, curr['id']
            )
            count_updated += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Errore pallet {codice}: {e}")

    mssql_conn.commit()

    print(f"   🔄 {count_updated} pallet aggiornati")
    print(f"   ⏸️ {count_unchanged} invariati")
    print(f"   ⏭️ {count_skipped} saltati (codice non trovato in MSSQL)")
    if errors > 0:
        print(f"   ⚠️ {errors} errori")

    return count_updated


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Sync incrementale assegnazioni pallet e testate')
    parser.add_argument('--sync', dest='do_sync', action='store_true',
                        help='Esegui sync incrementale assegnazioni')
    parser.add_argument('--sync-buyer', dest='do_sync_buyer', action='store_true',
                        help='Aggiorna buyer_id in shared.pallet da TPallet Access')
    parser.add_argument('--test', dest='use_test', action='store_true',
                        help='Usa DjangoIntranet-test invece di produzione')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                        help='Mostra cosa verrebbe modificato senza applicare nulla')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SYNC INCREMENTALE ASSEGNAZIONI PALLET E TESTATE")
    print("(Aggiorna esistenti, inserisce nuovi, NON cancella)")
    print("=" * 60)
    db_name = MSSQL_DATABASE_TEST if args.use_test else MSSQL_DATABASE_PROD
    print(f"File Access: {ACCESS_FILE}")
    print(f"Database MSSQL: {db_name}{' [TEST]' if args.use_test else ' [PRODUZIONE]'}")
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
        mssql_conn = get_mssql_conn(test=args.use_test)
        mssql_cur = mssql_conn.cursor()
        print(f"✅ Connesso a MSSQL ({db_name})")
    except Exception as e:
        print(f"❌ Errore connessione MSSQL: {e}")
        return

    try:
        gold_conn = get_gold_conn()
        gold_cur = gold_conn.cursor()
        print(f"✅ Connesso a GoldReport ({MSSQL_DATABASE_GOLD})")
    except Exception as e:
        print(f"❌ Errore connessione GoldReport: {e}")
        return
    
    # Verifica
    verify_access(access_cur)
    verify_mssql(mssql_cur)
    
    # Sync buyer pallet
    if args.do_sync_buyer:
        print("\n" + "=" * 60)
        print("ℹ️  SYNC BUYER PALLET:")
        print("   - Aggiorna buyer_id in shared.pallet da TPallet Access")
        print("=" * 60)

        confirm = input("\n🟢 Confermi sync buyer pallet? (s/N): ")
        if confirm.lower() == 's':
            sync_buyer_pallet(access_cur, mssql_cur, mssql_conn)
            print("\n✅ SYNC BUYER PALLET COMPLETATO!")
        else:
            print("\n❌ Sync annullato")

    # Sync
    if args.do_sync:
        print("\n" + "=" * 60)
        print("ℹ️  SYNC INCREMENTALE:")
        print("   - Aggiorna record esistenti se modificati")
        print("   - Inserisce nuovi record")
        print("   - NON cancella nulla")
        print("=" * 60)
        
        if args.dry_run:
            print("\n🔍 DRY-RUN: nessuna modifica verrà applicata al DB\n")
            sync_pallet(access_cur, mssql_cur, mssql_conn, gold_cur, dry_run=True)
            sync_testate(access_cur, mssql_cur, mssql_conn, dry_run=True)
        else:
            confirm = input("\n🟢 Confermi sync? (s/N): ")
            if confirm.lower() == 's':
                sync_pallet(access_cur, mssql_cur, mssql_conn, gold_cur)
                sync_testate(access_cur, mssql_cur, mssql_conn)

                print("\n" + "=" * 60)
                print("✅ SYNC COMPLETATO!")
                print("=" * 60)

                verify_mssql(mssql_cur)
            else:
                print("\n❌ Sync annullato")
    else:
        print("\n💡 Per sincronizzare, esegui: python sync_assegnazioni.py --sync")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()
    gold_conn.close()

if __name__ == '__main__':
    main()
