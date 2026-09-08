"""
Script per sincronizzare testate da Access a Django

Aggiunge testate mancanti da TTestate_New a shared.testate

Uso:
    python sync_testate.py              # Solo verifica
    python sync_testate.py --sync       # Verifica + Sync
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
    parser = argparse.ArgumentParser(description='Sync testate da Access')
    parser.add_argument('--sync', dest='do_sync', action='store_true', 
                        help='Esegui sync')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SYNC TESTATE")
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
    
    # Leggi testate esistenti in Django
    mssql_cur.execute("SELECT id, locazione, bloccata FROM shared.testate")
    django_testate = {row[0]: {'locazione': row[1], 'bloccata': row[2]} for row in mssql_cur.fetchall()}
    print(f"\n📦 Testate in Django: {len(django_testate)}")
    
    # Leggi testate da Access TTestate_New (unica fonte)
    access_cur.execute("SELECT * FROM TTestate_New")
    access_testate = {}
    for row in access_cur.fetchall():
        id_testata = row[0]
        descrizione = row[1] if row[1] else f"Testata {id_testata}"
        bloccata = bool(row[2]) if len(row) > 2 else False
        access_testate[id_testata] = {'locazione': descrizione, 'bloccata': bloccata}
    print(f"📦 Testate in TTestate_New: {len(access_testate)}")
    
    # Trova mancanti e da aggiornare
    mancanti = []
    da_aggiornare = []
    for id_t, data in access_testate.items():
        if id_t not in django_testate:
            mancanti.append((id_t, data['locazione'], data['bloccata']))
        else:
            # Controlla se locazione o bloccata sono diversi
            dj = django_testate[id_t]
            if dj['locazione'] != data['locazione'] or dj['bloccata'] != data['bloccata']:
                da_aggiornare.append((id_t, data['locazione'], data['bloccata'], dj['locazione']))
    
    print(f"\n🆕 Testate da aggiungere: {len(mancanti)}")
    for id_t, loc, blocc in sorted(mancanti):
        status = "🔒" if blocc else "  "
        print(f"   {status} {id_t}: {loc}")
    
    print(f"\n🔄 Testate da aggiornare: {len(da_aggiornare)}")
    for id_t, loc_new, blocc, loc_old in sorted(da_aggiornare):
        status = "🔒" if blocc else "  "
        print(f"   {status} {id_t}: '{loc_old}' → '{loc_new}'")
    
    # Trova testate obsolete (in Django ma non in TTestate_New)
    obsolete = []
    for id_t, data in django_testate.items():
        if id_t not in access_testate and not data['bloccata']:
            obsolete.append((id_t, data['locazione']))
    
    print(f"\n🚫 Testate obsolete (da bloccare): {len(obsolete)}")
    for id_t, loc in sorted(obsolete):
        print(f"   🔒 {id_t}: {loc}")
    
    # Sync
    if args.do_sync and (mancanti or da_aggiornare or obsolete):
        print("\n" + "=" * 60)
        confirm = input("🟢 Confermi sync? (s/N): ")
        if confirm.lower() == 's':
            count_inserted = 0
            count_updated = 0
            count_blocked = 0
            
            for id_t, loc, blocc in mancanti:
                try:
                    mssql_cur.execute("""
                        INSERT INTO shared.testate (id, locazione, bloccata)
                        VALUES (?, ?, ?)
                    """, id_t, loc, blocc)
                    count_inserted += 1
                except Exception as e:
                    print(f"   ⚠️ Errore inserimento {id_t}: {e}")
            
            for id_t, loc, blocc, _ in da_aggiornare:
                try:
                    mssql_cur.execute("""
                        UPDATE shared.testate SET locazione = ?, bloccata = ? WHERE id = ?
                    """, loc, blocc, id_t)
                    count_updated += 1
                except Exception as e:
                    print(f"   ⚠️ Errore aggiornamento {id_t}: {e}")
            
            for id_t, _ in obsolete:
                try:
                    mssql_cur.execute("""
                        UPDATE shared.testate SET bloccata = 1 WHERE id = ?
                    """, id_t)
                    count_blocked += 1
                except Exception as e:
                    print(f"   ⚠️ Errore blocco {id_t}: {e}")
            
            mssql_conn.commit()
            
            print(f"\n✅ {count_inserted} testate inserite")
            print(f"✅ {count_updated} testate aggiornate")
            print(f"✅ {count_blocked} testate obsolete bloccate")
            
            # Verifica finale
            mssql_cur.execute("SELECT COUNT(*) FROM shared.testate")
            print(f"\n📦 Testate in Django ora: {mssql_cur.fetchone()[0]}")
        else:
            print("\n❌ Sync annullato")
    elif not mancanti and not da_aggiornare:
        print("\n✅ Nessuna modifica necessaria")
    else:
        print("\n💡 Per sincronizzare, esegui: python sync_testate.py --sync")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
