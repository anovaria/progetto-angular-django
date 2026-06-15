"""
Script di SYNC T_Merchandiser → shared.merchandiser

SYNC INCREMENTALE: aggiorna esistenti, inserisce nuovi, NON cancella.
ATTENZIONE: Gestisce conflitti ID (Django può avere ID diversi da Access)

Uso:
    python sync_merchandiser.py              # Solo verifica
    python sync_merchandiser.py --sync       # Verifica + Sync
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
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Sync anagrafica merchandiser')
    parser.add_argument('--sync', dest='do_sync', action='store_true', 
                        help='Esegui sync')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SYNC ANAGRAFICA MERCHANDISER")
    print("T_Merchandiser → shared.merchandiser")
    print("=" * 60)
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
    print("\n" + "=" * 60)
    print("📊 ANALISI ACCESS")
    print("=" * 60)
    
    access_cur.execute("SELECT COUNT(*) FROM T_Merchandiser")
    access_count = access_cur.fetchone()[0]
    print(f"📦 T_Merchandiser: {access_count} record")
    
    access_cur.execute("SELECT MAX(ID) FROM T_Merchandiser")
    max_id_access = access_cur.fetchone()[0]
    print(f"   Max ID: {max_id_access}")
    
    # Verifica MSSQL
    print("\n" + "=" * 60)
    print("📊 ANALISI MSSQL")
    print("=" * 60)
    
    mssql_cur.execute("SELECT COUNT(*) FROM shared.merchandiser")
    mssql_count = mssql_cur.fetchone()[0]
    print(f"📦 shared.merchandiser: {mssql_count} record")
    
    mssql_cur.execute("SELECT MAX(id) FROM shared.merchandiser")
    max_id_mssql = mssql_cur.fetchone()[0]
    print(f"   Max ID: {max_id_mssql}")
    
    # Carica esistenti MSSQL per cognome+nome (più affidabile dell'ID)
    print("\n📥 Caricamento dati esistenti...")
    mssql_cur.execute("""
        SELECT id, cognome, nome, attivo
        FROM shared.merchandiser
    """)
    
    existing_by_id = {}
    existing_by_name = {}
    for row in mssql_cur.fetchall():
        existing_by_id[row[0]] = {
            'cognome': row[1],
            'nome': row[2],
            'attivo': row[3]
        }
        key_name = (row[1].upper().strip() if row[1] else '', row[2].upper().strip() if row[2] else '')
        existing_by_name[key_name] = row[0]  # Mappa nome -> ID
    
    print(f"   MSSQL esistenti: {len(existing_by_id)}")
    
    # Leggi da Access
    print("📥 Lettura Access...")
    access_cur.execute("""
        SELECT ID, Cognome, Nome
        FROM T_Merchandiser
        WHERE Cognome IS NOT NULL
    """)
    
    count_to_insert = 0
    count_to_update = 0
    count_conflict = 0
    count_unchanged = 0
    to_insert = []
    to_update = []
    conflicts = []
    
    for row in access_cur.fetchall():
        access_id = row[0]
        cognome = row[1].strip() if row[1] else ''
        nome = row[2].strip() if row[2] else ''
        
        key_name = (cognome.upper(), nome.upper())
        
        # Cerca per nome prima
        if key_name in existing_by_name:
            django_id = existing_by_name[key_name]
            if django_id == access_id:
                # Stesso ID, tutto ok
                count_unchanged += 1
            else:
                # ID diverso - conflitto
                conflicts.append({
                    'access_id': access_id,
                    'django_id': django_id,
                    'cognome': cognome,
                    'nome': nome
                })
                count_conflict += 1
        elif access_id in existing_by_id:
            # L'ID esiste ma con nome diverso - conflitto
            curr = existing_by_id[access_id]
            conflicts.append({
                'access_id': access_id,
                'django_id': access_id,
                'access_name': f"{cognome} {nome}",
                'django_name': f"{curr['cognome']} {curr['nome']}",
                'type': 'id_conflict'
            })
            count_conflict += 1
        else:
            # Nuovo merchandiser
            to_insert.append((access_id, cognome, nome))
            count_to_insert += 1
    
    print(f"\n🆕 Da inserire: {count_to_insert}")
    print(f"🔄 Da aggiornare: {count_to_update}")
    print(f"⚠️ Conflitti ID: {count_conflict}")
    print(f"⏸️ Invariati: {count_unchanged}")
    
    # Mostra conflitti
    if conflicts:
        print("\n⚠️ CONFLITTI RILEVATI:")
        for c in conflicts[:10]:
            if c.get('type') == 'id_conflict':
                print(f"   ID {c['access_id']}: Access='{c['access_name']}' vs Django='{c['django_name']}'")
            else:
                print(f"   '{c['cognome']} {c['nome']}': Access ID={c['access_id']}, Django ID={c['django_id']}")
    
    # Mostra da inserire
    if to_insert:
        print("\n   Da inserire:")
        for row in to_insert[:10]:
            print(f"      ID {row[0]}: {row[1]} {row[2]}")
    
    # Sync
    if args.do_sync and to_insert:
        print("\n" + "=" * 60)
        print("⚠️ NOTA: I conflitti di ID NON verranno risolti automaticamente.")
        print("   Solo i nuovi merchandiser verranno inseriti.")
        confirm = input("🟢 Confermi sync? (s/N): ")
        if confirm.lower() == 's':
            errors = 0
            inserted = 0
            
            # Verifica se serve IDENTITY_INSERT
            mssql_cur.execute("SET IDENTITY_INSERT shared.merchandiser ON")
            
            for row in to_insert:
                try:
                    mssql_cur.execute("""
                        INSERT INTO shared.merchandiser 
                        (id, cognome, nome, attivo)
                        VALUES (?, ?, ?, 1)
                    """, row[0], row[1], row[2])
                    inserted += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"   ⚠️ Errore insert ID {row[0]}: {e}")
            
            mssql_cur.execute("SET IDENTITY_INSERT shared.merchandiser OFF")
            mssql_conn.commit()
            
            print(f"\n✅ {inserted} merchandiser inseriti")
            if errors > 0:
                print(f"⚠️ {errors} errori")
            
            # Verifica finale
            mssql_cur.execute("SELECT COUNT(*) FROM shared.merchandiser")
            print(f"\n📦 Totale MSSQL ora: {mssql_cur.fetchone()[0]}")
        else:
            print("\n❌ Sync annullato")
    elif not to_insert:
        print("\n✅ Nessun nuovo merchandiser da inserire")
        if conflicts:
            print("⚠️ Ci sono conflitti da risolvere manualmente")
    else:
        print("\n💡 Per sincronizzare, esegui: python sync_merchandiser.py --sync")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
