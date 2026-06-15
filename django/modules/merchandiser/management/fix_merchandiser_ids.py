"""
Script per RIALLINEARE ID merchandiser Django → Access

Risolve i conflitti di ID tra Django e Access:
1. Trova merchandiser con stesso nome ma ID diverso
2. Aggiorna gli ID in shared.merchandiser
3. Aggiorna i riferimenti in shared.slot
4. Aggiorna i riferimenti in shared.slot_ingressi_uscite

Uso:
    python fix_merchandiser_ids.py              # Solo verifica
    python fix_merchandiser_ids.py --fix        # Verifica + Fix
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
    parser = argparse.ArgumentParser(description='Fix ID merchandiser')
    parser.add_argument('--fix', dest='do_fix', action='store_true', 
                        help='Esegui fix')
    args = parser.parse_args()
    
    print("=" * 70)
    print("FIX ID MERCHANDISER - Riallineamento Django → Access")
    print("=" * 70)
    print(f"Data esecuzione: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70)
    
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
    
    # Carica merchandiser Access
    print("\n📥 Caricamento Access...")
    access_cur.execute("SELECT ID, Cognome, Nome FROM T_Merchandiser WHERE Cognome IS NOT NULL")
    access_merch = {}
    for row in access_cur.fetchall():
        key = (row[1].upper().strip() if row[1] else '', row[2].upper().strip() if row[2] else '')
        access_merch[key] = row[0]
    print(f"   Access: {len(access_merch)} merchandiser")
    
    # Carica merchandiser Django
    print("📥 Caricamento Django...")
    mssql_cur.execute("SELECT id, cognome, nome FROM shared.merchandiser")
    django_merch = {}
    for row in mssql_cur.fetchall():
        key = (row[1].upper().strip() if row[1] else '', row[2].upper().strip() if row[2] else '')
        django_merch[key] = row[0]
    print(f"   Django: {len(django_merch)} merchandiser")
    
    # Trova conflitti (stesso nome, ID diverso)
    conflicts = []
    for key, access_id in access_merch.items():
        if key in django_merch:
            django_id = django_merch[key]
            if access_id != django_id:
                conflicts.append({
                    'cognome': key[0],
                    'nome': key[1],
                    'access_id': access_id,
                    'django_id': django_id
                })
    
    # Trova merchandiser solo in Access (da inserire)
    to_insert = []
    for key, access_id in access_merch.items():
        if key not in django_merch:
            to_insert.append({
                'id': access_id,
                'cognome': key[0],
                'nome': key[1]
            })
    
    print(f"\n⚠️ Conflitti ID: {len(conflicts)}")
    print(f"🆕 Da inserire: {len(to_insert)}")
    
    if conflicts:
        print("\n📋 CONFLITTI:")
        print(f"   {'Nome':<35} {'Access ID':>10} {'Django ID':>10}")
        print("   " + "-" * 57)
        for c in conflicts:
            nome_completo = f"{c['cognome']} {c['nome']}"[:35]
            print(f"   {nome_completo:<35} {c['access_id']:>10} {c['django_id']:>10}")
    
    if to_insert:
        print(f"\n📋 DA INSERIRE:")
        for m in to_insert[:10]:
            print(f"   ID {m['id']}: {m['cognome']} {m['nome']}")
        if len(to_insert) > 10:
            print(f"   ... e altri {len(to_insert) - 10}")
    
    # Conta record collegati per ogni conflitto
    if conflicts and args.do_fix:
        print("\n📊 Analisi impatto:")
        for c in conflicts:
            mssql_cur.execute("SELECT COUNT(*) FROM shared.slot WHERE merchandiser_id = ?", c['django_id'])
            slot_count = mssql_cur.fetchone()[0]
            mssql_cur.execute("SELECT COUNT(*) FROM shared.slot_ingressi_uscite WHERE slot_id IN (SELECT id FROM shared.slot WHERE merchandiser_id = ?)", c['django_id'])
            orari_count = mssql_cur.fetchone()[0]
            c['slot_count'] = slot_count
            c['orari_count'] = orari_count
            if slot_count > 0:
                print(f"   {c['cognome']} {c['nome']}: {slot_count} slot, {orari_count} orari")
    
    # Fix
    if args.do_fix and (conflicts or to_insert):
        print("\n" + "=" * 70)
        print("⚠️ ATTENZIONE: Questo script modificherà:")
        print("   1. ID merchandiser in shared.merchandiser")
        print("   2. Riferimenti merchandiser_id in shared.slot")
        print("   (Gli orari sono collegati allo slot, non al merchandiser)")
        print("=" * 70)
        confirm = input("🔴 Confermi? (scrivi 'SI' per confermare): ")
        
        if confirm == 'SI':
            errors = 0
            fixed = 0
            inserted = 0
            
            # Prima inserisci i nuovi (che non hanno conflitti)
            if to_insert:
                print("\n📥 Inserimento nuovi merchandiser...")
                mssql_cur.execute("SET IDENTITY_INSERT shared.merchandiser ON")
                for m in to_insert:
                    try:
                        # Verifica che l'ID non esista già
                        mssql_cur.execute("SELECT id FROM shared.merchandiser WHERE id = ?", m['id'])
                        if mssql_cur.fetchone():
                            print(f"   ⚠️ ID {m['id']} già esistente, skip")
                            continue
                        
                        mssql_cur.execute("""
                            INSERT INTO shared.merchandiser (id, cognome, nome, attivo)
                            VALUES (?, ?, ?, 1)
                        """, m['id'], m['cognome'].title(), m['nome'].title())
                        inserted += 1
                    except Exception as e:
                        errors += 1
                        print(f"   ⚠️ Errore insert {m['id']}: {e}")
                mssql_cur.execute("SET IDENTITY_INSERT shared.merchandiser OFF")
                mssql_conn.commit()
                print(f"   ✅ {inserted} inseriti")
            
            # Fix conflitti
            if conflicts:
                print("\n🔧 Fix conflitti ID...")
                for c in conflicts:
                    old_id = c['django_id']
                    new_id = c['access_id']
                    
                    try:
                        # Usa un ID temporaneo negativo per evitare conflitti
                        temp_id = -old_id
                        
                        # 1. Aggiorna slot al temp_id
                        mssql_cur.execute("""
                            UPDATE shared.slot SET merchandiser_id = ? WHERE merchandiser_id = ?
                        """, temp_id, old_id)
                        
                        # 2. Elimina il vecchio merchandiser
                        mssql_cur.execute("DELETE FROM shared.merchandiser WHERE id = ?", old_id)
                        
                        # 3. Verifica se new_id esiste già
                        mssql_cur.execute("SELECT id FROM shared.merchandiser WHERE id = ?", new_id)
                        if mssql_cur.fetchone():
                            # Esiste già con ID corretto, aggiorna solo gli slot
                            mssql_cur.execute("""
                                UPDATE shared.slot SET merchandiser_id = ? WHERE merchandiser_id = ?
                            """, new_id, temp_id)
                        else:
                            # Inserisci con nuovo ID
                            mssql_cur.execute("SET IDENTITY_INSERT shared.merchandiser ON")
                            mssql_cur.execute("""
                                INSERT INTO shared.merchandiser (id, cognome, nome, attivo)
                                VALUES (?, ?, ?, 1)
                            """, new_id, c['cognome'].title(), c['nome'].title())
                            mssql_cur.execute("SET IDENTITY_INSERT shared.merchandiser OFF")
                            
                            # Aggiorna slot al nuovo ID
                            mssql_cur.execute("""
                                UPDATE shared.slot SET merchandiser_id = ? WHERE merchandiser_id = ?
                            """, new_id, temp_id)
                        
                        mssql_conn.commit()
                        fixed += 1
                        print(f"   ✅ {c['cognome']} {c['nome']}: {old_id} → {new_id}")
                        
                    except Exception as e:
                        mssql_conn.rollback()
                        errors += 1
                        print(f"   ❌ Errore {c['cognome']} {c['nome']}: {e}")
            
            print(f"\n✅ {fixed} conflitti risolti")
            print(f"✅ {inserted} nuovi inseriti")
            if errors > 0:
                print(f"⚠️ {errors} errori")
            
            # Verifica finale
            mssql_cur.execute("SELECT COUNT(*) FROM shared.merchandiser")
            print(f"\n📦 Totale merchandiser ora: {mssql_cur.fetchone()[0]}")
            
        else:
            print("\n❌ Operazione annullata")
    else:
        if not args.do_fix:
            print("\n💡 Per applicare i fix, esegui: python fix_merchandiser_ids.py --fix")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
