"""
Script di migrazione dati da Access a MSSQL (Windows)
Pallet-Promoter + Merchandiser
ATTENZIONE: è uno script Python standalone (usa direttamente pyodbc, non passa da Django)
Uso:
    python migrate_to_mssql.py

Modifica le variabili ACCESS_FILE e MSSQL_* prima di eseguire.

Prerequisiti:
    pip install pyodbc
"""

import pyodbc
from datetime import datetime

# ============================================
# CONFIGURAZIONE - MODIFICA QUESTI VALORI
# ============================================

ACCESS_FILE = r"C:\portale\backend\modules\pallet_promoter\management\Pallet_Promoter.accdb"  # <-- MODIFICA

MSSQL_SERVER = "srviisnew"  # o nome server
MSSQL_DATABASE = "DjangoIntranet"
MSSQL_DRIVER = "ODBC Driver 18 for SQL Server"

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
        f"UID=django_user;"
        f"PWD=Sangiovese.2025@@;"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

# ============================================
# MIGRAZIONE PALLET-PROMOTER (esistenti)
# ============================================

def migrate_agenzie(access_cur, mssql_cur):
    print("\n📦 T_Agenzie → shared.agenzie")
    mssql_cur.execute("DELETE FROM shared.agenzie")
    
    access_cur.execute("SELECT ID, Descrizione, Nota FROM T_Agenzie")
    rows = access_cur.fetchall()
    
    for row in rows:
        mssql_cur.execute(
            "INSERT INTO shared.agenzie (id, descrizione, nota) VALUES (?, ?, ?)",
            row.ID, row.Descrizione, row.Nota
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def migrate_reparti(access_cur, mssql_cur):
    print("\n📦 T_Reparti → shared.reparti")
    mssql_cur.execute("DELETE FROM shared.reparti")
    
    access_cur.execute("SELECT IDReparto, DescrReparto FROM T_Reparti")
    rows = access_cur.fetchall()
    
    for row in rows:
        mssql_cur.execute(
            "INSERT INTO shared.reparti (id, descrizione) VALUES (?, ?)",
            row.IDReparto, row.DescrReparto
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def migrate_buyer(access_cur, mssql_cur):
    print("\n📦 TBuyer → shared.buyer")
    mssql_cur.execute("DELETE FROM shared.buyer")
    
    access_cur.execute("SELECT ID, Nominativo, BuyerAs400 FROM TBuyer")
    rows = access_cur.fetchall()
    
    for row in rows:
        mssql_cur.execute(
            "INSERT INTO shared.buyer (id, nominativo, codice_as400) VALUES (?, ?, ?)",
            row.ID, row.Nominativo, row.BuyerAs400
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def migrate_hostess(access_cur, mssql_cur):
    print("\n📦 THostess → shared.hostess")
    mssql_cur.execute("DELETE FROM shared.hostess")
    
    access_cur.execute("SELECT ID, Nominativo, Ruolo, Nota, ExLibSan FROM THostess")
    rows = access_cur.fetchall()
    
    for row in rows:
        mssql_cur.execute(
            "INSERT INTO shared.hostess (id, nominativo, ruolo, nota, scadenza_libretto_sanitario, attiva) VALUES (?, ?, ?, ?, ?, ?)",
            row.ID, row.Nominativo, row.Ruolo, row.Nota, row.ExLibSan, 1
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def migrate_fornitori(access_cur, mssql_cur):
    print("\n📦 TFornitori → shared.fornitori")
    mssql_cur.execute("DELETE FROM shared.fornitori")
    
    access_cur.execute("SELECT FCODFO, FNOMFO, BUYER, FREPAR, CCOM FROM TFornitori")
    rows = access_cur.fetchall()
    
    count = 0
    for row in rows:
        try:
            mssql_cur.execute(
                "INSERT INTO shared.fornitori (codice, nome, buyer, reparto, codice_commerciale) VALUES (?, ?, ?, ?, ?)",
                row.FCODFO, row.FNOMFO, row.BUYER, row.FREPAR, row.CCOM
            )
            count += 1
        except Exception as e:
            pass  # Skip duplicati
    print(f"   ✅ {count} record")
    return count


def migrate_pallet(access_cur, mssql_cur):
    print("\n📦 TPallet → shared.pallet")
    mssql_cur.execute("DELETE FROM shared.pallet")
    
    access_cur.execute("SELECT Descrizione, CoordX, CoordY, NumBuyer, Dimensione FROM TPallet")
    rows = access_cur.fetchall()
    
    for row in rows:
        mssql_cur.execute(
            "INSERT INTO shared.pallet (codice, coord_x, coord_y, buyer_id, dimensione) VALUES (?, ?, ?, ?, ?)",
            row.Descrizione, row.CoordX or 0, row.CoordY or 0, row.NumBuyer, row.Dimensione or 0
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def migrate_testate(access_cur, mssql_cur):
    print("\n📦 TTestate → shared.testate")
    mssql_cur.execute("DELETE FROM shared.testate")
    
    access_cur.execute("SELECT ID, [Locazione testata] FROM TTestate")
    rows = access_cur.fetchall()
    
    for row in rows:
        mssql_cur.execute(
            "INSERT INTO shared.testate (id, locazione, bloccata) VALUES (?, ?, ?)",
            row.ID, row[1], 0
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def migrate_banchi(access_cur, mssql_cur):
    print("\n📦 TBanchi → shared.banchi")
    mssql_cur.execute("DELETE FROM shared.banchi")
    
    try:
        access_cur.execute("SELECT ID, Descrizione FROM TBanchi")
        rows = access_cur.fetchall()
        
        for row in rows:
            mssql_cur.execute(
                "INSERT INTO shared.banchi (id, descrizione) VALUES (?, ?)",
                row.ID, row.Descrizione
            )
        print(f"   ✅ {len(rows)} record")
        return len(rows)
    except:
        print("   ⚠️  Tabella non trovata o vuota")
        return 0


def migrate_periodi(access_cur, mssql_cur):
    print("\n📦 TPeriodiSellOut → shared.periodi")
    mssql_cur.execute("DELETE FROM shared.periodi")
    
    access_cur.execute("SELECT IDPeriodo, AnnoRif, CodPromo, [Data Inizio], [Data Fine], NHostess FROM TPeriodiSellOut")
    rows = access_cur.fetchall()
    
    for row in rows:
        codice = f"P-{row.CodPromo}" if row.CodPromo else f"P-{row.IDPeriodo}"
        descrizione = f"Periodo {row.CodPromo}"
        
        mssql_cur.execute(
            "INSERT INTO shared.periodi (codice, codice_promozione, descrizione, data_inizio, data_fine, anno, num_hostess) VALUES (?, ?, ?, ?, ?, ?, ?)",
            codice, row.IDPeriodo, descrizione, row[3], row[4], row.AnnoRif, row.NHostess or 8
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


# ============================================
# MIGRAZIONE MERCHANDISER (nuove)
# ============================================

def migrate_attivita(access_cur, mssql_cur):
    print("\n📦 T_Attività → shared.attivita")
    mssql_cur.execute("DELETE FROM shared.attivita")
    
    try:
        access_cur.execute("SELECT ID, Descrizione FROM T_Attività")
        rows = access_cur.fetchall()
        
        for row in rows:
            mssql_cur.execute(
                "INSERT INTO shared.attivita (id, descrizione) VALUES (?, ?)",
                row.ID, row.Descrizione
            )
        print(f"   ✅ {len(rows)} record")
        return len(rows)
    except Exception as e:
        print(f"   ⚠️  Errore: {e}")
        return 0


def migrate_merchandiser(access_cur, mssql_cur):
    print("\n📦 T_Merchandiser → shared.merchandiser")
    mssql_cur.execute("DELETE FROM shared.merchandiser")
    
    try:
        access_cur.execute("SELECT ID, Cognome, Nome, Tel, Email, Note FROM T_Merchandiser")
        rows = access_cur.fetchall()
        
        for row in rows:
            mssql_cur.execute(
                "INSERT INTO shared.merchandiser (id, cognome, nome, telefono, email, note, attivo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                row.ID, row.Cognome, row.Nome, row.Tel, row.Email, row.Note, 1
            )
        print(f"   ✅ {len(rows)} record")
        return len(rows)
    except Exception as e:
        print(f"   ⚠️  Errore: {e}")
        return 0


def migrate_slot(access_cur, mssql_cur):
    print("\n📦 T_Slot → shared.slot")
    mssql_cur.execute("DELETE FROM shared.slot")
    
    try:
        access_cur.execute("""
            SELECT ID, codeMerchandiser, codeUtente, DataInizio, DataFine,
                   Lun, Mar, Mer, Gio, Ven, Sab, Dom,
                   Note, Docum, codeBadge, PlafondOre
            FROM T_Slot
            WHERE DataInizio IS NOT NULL AND DataFine IS NOT NULL
        """)
        rows = access_cur.fetchall()
        
        count = 0
        for row in rows:
            try:
                mssql_cur.execute("""
                    INSERT INTO shared.slot (id, merchandiser_id, utente_id, data_inizio, data_fine,
                                            lun, mar, mer, gio, ven, sab, dom,
                                            note, documento, badge, plafond_ore)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    row.ID, row.codeMerchandiser, row.codeUtente, row.DataInizio, row.DataFine,
                    1 if row.Lun else 0, 1 if row.Mar else 0, 1 if row.Mer else 0,
                    1 if row.Gio else 0, 1 if row.Ven else 0, 1 if row.Sab else 0, 1 if row.Dom else 0,
                    row.Note, row.Docum, row.codeBadge, row.PlafondOre or 0
                )
                count += 1
            except Exception as e:
                pass  # Skip record con errori
        print(f"   ✅ {count} record")
        return count
    except Exception as e:
        print(f"   ⚠️  Errore: {e}")
        return 0


def migrate_slot_fornitori(access_cur, mssql_cur):
    print("\n📦 T_FornitoriSlot → shared.slot_fornitori")
    mssql_cur.execute("DELETE FROM shared.slot_fornitori")
    
    try:
        access_cur.execute("""
            SELECT codeSlot, codeAgenzia, codeFornitore, codeSRep, codeAttivita
            FROM T_FornitoriSlot
        """)
        rows = access_cur.fetchall()
        
        count = 0
        for row in rows:
            try:
                mssql_cur.execute("""
                    INSERT INTO shared.slot_fornitori (slot_id, agenzia_id, fornitore_id, sotto_reparto_id, attivita_id, buyer_id, note)
                    VALUES (?, ?, ?, NULL, ?, NULL, NULL)
                """,
                    row.codeSlot, row.codeAgenzia or None, row.codeFornitore or None,
                    row.codeAttivita or None
                )
                count += 1
            except Exception as e:
                pass  # Skip record con errori (es. slot_id non esistente)
        print(f"   ✅ {count} record")
        return count
    except Exception as e:
        print(f"   ⚠️  Errore: {e}")
        return 0


def migrate_slot_ingressi_uscite(access_cur, mssql_cur):
    print("\n📦 T_IngressiUscite_Polmone → shared.slot_ingressi_uscite")
    mssql_cur.execute("DELETE FROM shared.slot_ingressi_uscite")
    
    try:
        access_cur.execute("""
            SELECT codeSlot, Data, Ing1, Usc1, Ing2, Usc2, IngExtra1, UscExtra1
            FROM T_IngressiUscite_Polmone
        """)
        rows = access_cur.fetchall()
        
        count = 0
        for row in rows:
            try:
                mssql_cur.execute("""
                    INSERT INTO shared.slot_ingressi_uscite (slot_id, data, ingresso_1, uscita_1, ingresso_2, uscita_2, ingresso_extra, uscita_extra, forzato, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
                """,
                    row.codeSlot, row.Data,
                    row.Ing1, row.Usc1, row.Ing2, row.Usc2, row.IngExtra1, row.UscExtra1
                )
                count += 1
            except Exception as e:
                pass  # Skip errori (es. slot_id non esistente)
        print(f"   ✅ {count} record")
        return count
    except Exception as e:
        print(f"   ⚠️  Errore: {e}")
        return 0


# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("MIGRAZIONE ACCESS → MSSQL")
    print("Pallet-Promoter + Merchandiser")
    print("=" * 60)
    print(f"File Access: {ACCESS_FILE}")
    print(f"Database MSSQL: {MSSQL_DATABASE}")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
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
    
    # Migrazione
    total = 0
    
    def safe_identity_insert(cursor, table, on=True):
        """Prova a settare IDENTITY_INSERT, ignora se non supportato."""
        try:
            cursor.execute(f"SET IDENTITY_INSERT {table} {'ON' if on else 'OFF'}")
        except:
            pass  # Tabella non ha IDENTITY
    
    # Disabilita tutti i vincoli FK
    print("\n⚙️  Disabilito vincoli FK...")
    mssql_cur.execute("""
        EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'
    """)
    mssql_conn.commit()
    
    try:
        # Pallet-Promoter
        safe_identity_insert(mssql_cur, 'shared.agenzie', True)
        total += migrate_agenzie(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.agenzie', False)
        mssql_conn.commit()
        
        safe_identity_insert(mssql_cur, 'shared.reparti', True)
        total += migrate_reparti(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.reparti', False)
        mssql_conn.commit()
        
        safe_identity_insert(mssql_cur, 'shared.buyer', True)
        total += migrate_buyer(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.buyer', False)
        mssql_conn.commit()
        
        safe_identity_insert(mssql_cur, 'shared.hostess', True)
        total += migrate_hostess(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.hostess', False)
        mssql_conn.commit()
        
        total += migrate_fornitori(access_cur, mssql_cur)
        mssql_conn.commit()
        
        total += migrate_pallet(access_cur, mssql_cur)
        mssql_conn.commit()
        
        safe_identity_insert(mssql_cur, 'shared.testate', True)
        total += migrate_testate(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.testate', False)
        mssql_conn.commit()
        
        total += migrate_banchi(access_cur, mssql_cur)
        mssql_conn.commit()
        
        total += migrate_periodi(access_cur, mssql_cur)
        mssql_conn.commit()
        
        # Merchandiser
        print("\n" + "-" * 40)
        print("MIGRAZIONE TABELLE MERCHANDISER")
        print("-" * 40)
        
        safe_identity_insert(mssql_cur, 'shared.attivita', True)
        total += migrate_attivita(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.attivita', False)
        mssql_conn.commit()
        
        safe_identity_insert(mssql_cur, 'shared.merchandiser', True)
        total += migrate_merchandiser(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.merchandiser', False)
        mssql_conn.commit()
        
        safe_identity_insert(mssql_cur, 'shared.slot', True)
        total += migrate_slot(access_cur, mssql_cur)
        safe_identity_insert(mssql_cur, 'shared.slot', False)
        mssql_conn.commit()
        
        total += migrate_slot_fornitori(access_cur, mssql_cur)
        mssql_conn.commit()
        
        total += migrate_slot_ingressi_uscite(access_cur, mssql_cur)
        mssql_conn.commit()
        
    except Exception as e:
        print(f"\n❌ Errore durante migrazione: {e}")
        mssql_conn.rollback()
    
    # Riabilita tutti i vincoli FK
    print("\n⚙️  Riabilito vincoli FK...")
    try:
        mssql_cur.execute("""
            EXEC sp_MSforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT ALL'
        """)
        mssql_conn.commit()
    except:
        pass
    
    # Chiudi connessioni
    access_conn.close()
    mssql_conn.close()
    
    print("\n" + "=" * 60)
    print(f"COMPLETATO! Totale record migrati: {total}")
    print("=" * 60)


if __name__ == '__main__':
    main()