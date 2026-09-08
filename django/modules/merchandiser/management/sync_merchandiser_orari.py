"""
Script di SYNC T_IngressiUscite → shared.slot_ingressi_uscite

SYNC INCREMENTALE: aggiorna esistenti, inserisce nuovi, NON cancella.

Uso:
    python sync_merchandiser_orari.py              # Solo verifica
    python sync_merchandiser_orari.py --sync       # Verifica + Sync
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

def time_to_str(t):
    """Converte time in stringa per confronto."""
    if t is None:
        return None
    return t.strftime('%H:%M:%S')

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Sync orari merchandiser')
    parser.add_argument('--sync', dest='do_sync', action='store_true', 
                        help='Esegui sync')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SYNC ORARI MERCHANDISER")
    print("T_IngressiUscite → shared.slot_ingressi_uscite")
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
    
    access_cur.execute("SELECT COUNT(*) FROM T_IngressiUscite")
    access_count = access_cur.fetchone()[0]
    print(f"📦 T_IngressiUscite: {access_count} record")
    
    access_cur.execute("SELECT MAX(Data) FROM T_IngressiUscite")
    max_date = access_cur.fetchone()[0]
    print(f"   Ultima data: {max_date}")
    
    # Verifica MSSQL
    print("\n" + "=" * 60)
    print("📊 ANALISI MSSQL")
    print("=" * 60)
    
    mssql_cur.execute("SELECT COUNT(*) FROM shared.slot_ingressi_uscite")
    mssql_count = mssql_cur.fetchone()[0]
    print(f"📦 slot_ingressi_uscite: {mssql_count} record")
    
    mssql_cur.execute("SELECT MAX(data) FROM shared.slot_ingressi_uscite")
    max_date_mssql = mssql_cur.fetchone()[0]
    print(f"   Ultima data: {max_date_mssql}")
    
    # Carica esistenti MSSQL
    # Colonne: id, slot_id, data, ingresso_1, uscita_1, ingresso_2, uscita_2, ingresso_extra, uscita_extra, forzato, note
    print("\n📥 Caricamento dati esistenti...")
    mssql_cur.execute("""
        SELECT slot_id, data, ingresso_1, uscita_1, ingresso_2, uscita_2,
               ingresso_extra, uscita_extra, forzato
        FROM shared.slot_ingressi_uscite
    """)
    
    existing = {}
    for row in mssql_cur.fetchall():
        key = (row[0], row[1])  # (slot_id, data)
        existing[key] = {
            'ingresso_1': time_to_str(row[2]),
            'uscita_1': time_to_str(row[3]),
            'ingresso_2': time_to_str(row[4]),
            'uscita_2': time_to_str(row[5]),
            'ingresso_extra': time_to_str(row[6]),
            'uscita_extra': time_to_str(row[7]),
            'forzato': row[8]
        }
    print(f"   MSSQL esistenti: {len(existing)}")
    
    # Leggi da Access
    # Colonne Access: codeSlot, Data, Ing1, Usc1, Ing2, Usc2, IngExtra1, UscExtra1, IngExtra2, UscExtra2, forced, chiave
    # MSSQL ha solo ingresso_extra e uscita_extra (singoli), quindi uso IngExtra1 e UscExtra1
    print("📥 Lettura Access...")
    access_cur.execute("""
        SELECT codeSlot, Data, Ing1, Usc1, Ing2, Usc2, 
               IngExtra1, UscExtra1, forced
        FROM T_IngressiUscite
        WHERE Data IS NOT NULL
    """)
    
    count_to_insert = 0
    count_to_update = 0
    count_unchanged = 0
    to_insert = []
    to_update = []
    
    for row in access_cur.fetchall():
        slot_id = row[0]
        data = row[1].date() if isinstance(row[1], datetime) else row[1]
        
        ing1 = parse_access_time(row[2])
        usc1 = parse_access_time(row[3])
        ing2 = parse_access_time(row[4])
        usc2 = parse_access_time(row[5])
        ing_ex = parse_access_time(row[6])
        usc_ex = parse_access_time(row[7])
        forzato = bool(row[8]) if row[8] is not None else False
        
        key = (slot_id, data)
        
        new_data = {
            'ingresso_1': time_to_str(ing1),
            'uscita_1': time_to_str(usc1),
            'ingresso_2': time_to_str(ing2),
            'uscita_2': time_to_str(usc2),
            'ingresso_extra': time_to_str(ing_ex),
            'uscita_extra': time_to_str(usc_ex),
            'forzato': forzato
        }
        
        if key in existing:
            # Confronta
            curr = existing[key]
            if (curr['ingresso_1'] != new_data['ingresso_1'] or
                curr['uscita_1'] != new_data['uscita_1'] or
                curr['ingresso_2'] != new_data['ingresso_2'] or
                curr['uscita_2'] != new_data['uscita_2'] or
                curr['ingresso_extra'] != new_data['ingresso_extra'] or
                curr['uscita_extra'] != new_data['uscita_extra']):
                to_update.append((slot_id, data, ing1, usc1, ing2, usc2, ing_ex, usc_ex, forzato))
                count_to_update += 1
            else:
                count_unchanged += 1
        else:
            to_insert.append((slot_id, data, ing1, usc1, ing2, usc2, ing_ex, usc_ex, forzato))
            count_to_insert += 1
    
    print(f"\n🆕 Da inserire: {count_to_insert}")
    print(f"🔄 Da aggiornare: {count_to_update}")
    print(f"⏸️ Invariati: {count_unchanged}")
    
    # Sync
    if args.do_sync and (to_insert or to_update):
        print("\n" + "=" * 60)
        confirm = input("🟢 Confermi sync? (s/N): ")
        if confirm.lower() == 's':
            errors = 0
            
            # Insert
            for row in to_insert:
                try:
                    mssql_cur.execute("""
                        INSERT INTO shared.slot_ingressi_uscite 
                        (slot_id, data, ingresso_1, uscita_1, ingresso_2, uscita_2,
                         ingresso_extra, uscita_extra, forzato)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, row)
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"   ⚠️ Errore insert slot {row[0]} data {row[1]}: {e}")
            
            # Update
            for row in to_update:
                try:
                    mssql_cur.execute("""
                        UPDATE shared.slot_ingressi_uscite 
                        SET ingresso_1 = ?, uscita_1 = ?, ingresso_2 = ?, uscita_2 = ?,
                            ingresso_extra = ?, uscita_extra = ?, forzato = ?
                        WHERE slot_id = ? AND data = ?
                    """, row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[0], row[1])
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"   ⚠️ Errore update slot {row[0]} data {row[1]}: {e}")
            
            mssql_conn.commit()
            
            print(f"\n✅ {count_to_insert} record inseriti")
            print(f"✅ {count_to_update} record aggiornati")
            if errors > 0:
                print(f"⚠️ {errors} errori")
            
            # Verifica finale
            mssql_cur.execute("SELECT COUNT(*) FROM shared.slot_ingressi_uscite")
            print(f"\n📦 Totale MSSQL ora: {mssql_cur.fetchone()[0]}")
        else:
            print("\n❌ Sync annullato")
    elif not to_insert and not to_update:
        print("\n✅ Nessuna modifica necessaria")
    else:
        print("\n💡 Per sincronizzare, esegui: python sync_merchandiser_orari.py --sync")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
