"""
Script di SYNC T_Slot → shared.slot

SYNC INCREMENTALE: aggiorna esistenti, inserisce nuovi, NON cancella.

Uso:
    python sync_merchandiser_slot.py              # Solo verifica
    python sync_merchandiser_slot.py --sync       # Verifica + Sync
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
    parser = argparse.ArgumentParser(description='Sync slot merchandiser')
    parser.add_argument('--sync', dest='do_sync', action='store_true', 
                        help='Esegui sync')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SYNC SLOT MERCHANDISER")
    print("T_Slot → shared.slot")
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
    
    access_cur.execute("SELECT COUNT(*) FROM T_Slot")
    access_count = access_cur.fetchone()[0]
    print(f"📦 T_Slot: {access_count} record")
    
    access_cur.execute("SELECT MAX(ID) FROM T_Slot")
    max_id_access = access_cur.fetchone()[0]
    print(f"   Max ID: {max_id_access}")
    
    # Verifica MSSQL
    print("\n" + "=" * 60)
    print("📊 ANALISI MSSQL")
    print("=" * 60)
    
    mssql_cur.execute("SELECT COUNT(*) FROM shared.slot")
    mssql_count = mssql_cur.fetchone()[0]
    print(f"📦 shared.slot: {mssql_count} record")
    
    mssql_cur.execute("SELECT MAX(id) FROM shared.slot")
    max_id_mssql = mssql_cur.fetchone()[0]
    print(f"   Max ID: {max_id_mssql}")
    
    # Carica esistenti MSSQL
    print("\n📥 Caricamento dati esistenti...")
    mssql_cur.execute("""
        SELECT id, merchandiser_id, data_inizio, data_fine, 
               lun, mar, mer, gio, ven, sab, dom, 
               note, badge, plafond_ore
        FROM shared.slot
    """)
    
    existing = {}
    for row in mssql_cur.fetchall():
        existing[row[0]] = {
            'merchandiser_id': row[1],
            'data_inizio': row[2],
            'data_fine': row[3],
            'lun': row[4], 'mar': row[5], 'mer': row[6], 
            'gio': row[7], 'ven': row[8], 'sab': row[9], 'dom': row[10],
            'note': row[11],
            'badge': row[12],
            'plafond_ore': row[13]
        }
    print(f"   MSSQL esistenti: {len(existing)}")
    
    # Leggi da Access - solo slot validi (con date e merchandiser)
    # Colonne: ID, codeMerchandiser, codeUtente, DataInizio, DataFine, Lun, Mar, Mer, Gio, Ven, Sab, Dom, Note, Docum, codeBadge, PlafondOre
    print("📥 Lettura Access (solo slot validi)...")
    access_cur.execute("""
        SELECT ID, codeMerchandiser, codeUtente, DataInizio, DataFine, 
               Lun, Mar, Mer, Gio, Ven, Sab, Dom, 
               Note, codeBadge, PlafondOre
        FROM T_Slot
        WHERE DataInizio IS NOT NULL AND DataFine IS NOT NULL AND codeMerchandiser IS NOT NULL
    """)
    
    count_to_insert = 0
    count_to_update = 0
    count_unchanged = 0
    to_insert = []
    to_update = []
    
    for row in access_cur.fetchall():
        slot_id = row[0]
        merchandiser_id = row[1]
        # codeUtente = row[2]  # Non usato in Django
        data_inizio = row[3].date() if isinstance(row[3], datetime) else row[3]
        data_fine = row[4].date() if isinstance(row[4], datetime) else row[4]
        lun = bool(row[5]) if row[5] is not None else False
        mar = bool(row[6]) if row[6] is not None else False
        mer = bool(row[7]) if row[7] is not None else False
        gio = bool(row[8]) if row[8] is not None else False
        ven = bool(row[9]) if row[9] is not None else False
        sab = bool(row[10]) if row[10] is not None else False
        dom = bool(row[11]) if row[11] is not None else False
        note = row[12] or ''
        badge = row[13] or ''
        plafond_ore = float(row[14]) if row[14] else 0.0
        
        new_data = {
            'merchandiser_id': merchandiser_id,
            'data_inizio': data_inizio,
            'data_fine': data_fine,
            'lun': lun, 'mar': mar, 'mer': mer,
            'gio': gio, 'ven': ven, 'sab': sab, 'dom': dom,
            'note': note,
            'badge': badge,
            'plafond_ore': plafond_ore
        }
        
        if slot_id in existing:
            # Confronta campi principali
            curr = existing[slot_id]
            if (curr['merchandiser_id'] != merchandiser_id or
                curr['data_inizio'] != data_inizio or
                curr['data_fine'] != data_fine or
                curr['lun'] != lun or curr['mar'] != mar or curr['mer'] != mer or
                curr['gio'] != gio or curr['ven'] != ven or curr['sab'] != sab or curr['dom'] != dom):
                to_update.append((slot_id, merchandiser_id, data_inizio, data_fine,
                                 lun, mar, mer, gio, ven, sab, dom, note, badge, plafond_ore))
                count_to_update += 1
            else:
                count_unchanged += 1
        else:
            to_insert.append((slot_id, merchandiser_id, data_inizio, data_fine,
                             lun, mar, mer, gio, ven, sab, dom, note, badge, plafond_ore))
            count_to_insert += 1
    
    print(f"\n🆕 Da inserire: {count_to_insert}")
    print(f"🔄 Da aggiornare: {count_to_update}")
    print(f"⏸️ Invariati: {count_unchanged}")
    
    # Mostra primi 10 da inserire
    if to_insert:
        print("\n   Primi 10 da inserire:")
        for row in to_insert[:10]:
            print(f"      ID {row[0]}: merchandiser {row[1]}, {row[2]} → {row[3]}")
    
    # Sync
    if args.do_sync and (to_insert or to_update):
        print("\n" + "=" * 60)
        confirm = input("🟢 Confermi sync? (s/N): ")
        if confirm.lower() == 's':
            errors = 0
            
            # Insert con IDENTITY_INSERT
            if to_insert:
                mssql_cur.execute("SET IDENTITY_INSERT shared.slot ON")
                for row in to_insert:
                    try:
                        mssql_cur.execute("""
                            INSERT INTO shared.slot 
                            (id, merchandiser_id, data_inizio, data_fine,
                             lun, mar, mer, gio, ven, sab, dom, note, badge, plafond_ore)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, row)
                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            print(f"   ⚠️ Errore insert slot {row[0]}: {e}")
                mssql_cur.execute("SET IDENTITY_INSERT shared.slot OFF")
            
            # Update
            for row in to_update:
                try:
                    mssql_cur.execute("""
                        UPDATE shared.slot 
                        SET merchandiser_id = ?, data_inizio = ?, data_fine = ?,
                            lun = ?, mar = ?, mer = ?, gio = ?, ven = ?, sab = ?, dom = ?,
                            note = ?, badge = ?, plafond_ore = ?
                        WHERE id = ?
                    """, row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[0])
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"   ⚠️ Errore update slot {row[0]}: {e}")
            
            mssql_conn.commit()
            
            print(f"\n✅ {count_to_insert} slot inseriti")
            print(f"✅ {count_to_update} slot aggiornati")
            if errors > 0:
                print(f"⚠️ {errors} errori")
            
            # Verifica finale
            mssql_cur.execute("SELECT COUNT(*) FROM shared.slot")
            print(f"\n📦 Totale MSSQL ora: {mssql_cur.fetchone()[0]}")
        else:
            print("\n❌ Sync annullato")
    elif not to_insert and not to_update:
        print("\n✅ Nessuna modifica necessaria")
    else:
        print("\n💡 Per sincronizzare, esegui: python sync_merchandiser_slot.py --sync")
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()

if __name__ == '__main__':
    main()
