"""
Script di esportazione dati da MSSQL a Access (Rollback)
Pallet-Promoter

Uso:
    python export_to_access.py

Modifica le variabili ACCESS_FILE e MSSQL_* prima di eseguire.

ATTENZIONE: Questo script SOVRASCRIVE i dati nel file Access!
Fare sempre un backup del file Access prima di eseguire.

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
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

# ============================================
# ESPORTAZIONE
# ============================================

def export_agenzie(mssql_cur, access_cur):
    print("\n📦 shared.agenzie → T_Agenzie")
    
    mssql_cur.execute("SELECT id, descrizione, nota FROM shared.agenzie")
    rows = mssql_cur.fetchall()
    
    for row in rows:
        access_cur.execute(
            "INSERT INTO T_Agenzie (ID, Descrizione, Nota) VALUES (?, ?, ?)",
            row.id, row.descrizione, row.nota
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def export_reparti(mssql_cur, access_cur):
    print("\n📦 shared.reparti → T_Reparti")
    
    mssql_cur.execute("SELECT id, descrizione FROM shared.reparti")
    rows = mssql_cur.fetchall()
    
    for row in rows:
        access_cur.execute(
            "INSERT INTO T_Reparti (IDReparto, DescrReparto) VALUES (?, ?)",
            row.id, row.descrizione
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def export_buyer(mssql_cur, access_cur):
    print("\n📦 shared.buyer → TBuyer")
    
    mssql_cur.execute("SELECT id, nominativo, codice_as400 FROM shared.buyer")
    rows = mssql_cur.fetchall()
    
    for row in rows:
        access_cur.execute(
            "INSERT INTO TBuyer (ID, Nominativo, BuyerAs400) VALUES (?, ?, ?)",
            row.id, row.nominativo, row.codice_as400
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def export_hostess(mssql_cur, access_cur):
    print("\n📦 shared.hostess → THostess")
    
    mssql_cur.execute("SELECT id, nominativo, ruolo, nota, scadenza_libretto_sanitario FROM shared.hostess")
    rows = mssql_cur.fetchall()
    
    for row in rows:
        access_cur.execute(
            "INSERT INTO THostess (ID, Nominativo, Ruolo, Nota, ExLibSan) VALUES (?, ?, ?, ?, ?)",
            row.id, row.nominativo, row.ruolo, row.nota, row.scadenza_libretto_sanitario
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def export_fornitori(mssql_cur, access_cur):
    print("\n📦 shared.fornitori → TFornitori")
    
    mssql_cur.execute("SELECT codice, nome, buyer, reparto, codice_commerciale FROM shared.fornitori")
    rows = mssql_cur.fetchall()
    
    count = 0
    for row in rows:
        try:
            access_cur.execute(
                "INSERT INTO TFornitori (FCODFO, FNOMFO, BUYER, FREPAR, CCOM) VALUES (?, ?, ?, ?, ?)",
                row.codice, row.nome, row.buyer, row.reparto, row.codice_commerciale
            )
            count += 1
        except Exception as e:
            pass  # Skip errori (es. duplicati)
    print(f"   ✅ {count} record")
    return count


def export_pallet(mssql_cur, access_cur):
    print("\n📦 shared.pallet → TPallet")
    
    mssql_cur.execute("SELECT codice, coord_x, coord_y, buyer_id, dimensione FROM shared.pallet")
    rows = mssql_cur.fetchall()
    
    for row in rows:
        access_cur.execute(
            "INSERT INTO TPallet (Descrizione, CoordX, CoordY, NumBuyer, Dimensione) VALUES (?, ?, ?, ?, ?)",
            row.codice, row.coord_x, row.coord_y, row.buyer_id, row.dimensione
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def export_testate(mssql_cur, access_cur):
    print("\n📦 shared.testate → TTestate")
    
    mssql_cur.execute("SELECT id, locazione FROM shared.testate")
    rows = mssql_cur.fetchall()
    
    for row in rows:
        access_cur.execute(
            "INSERT INTO TTestate (ID, [Locazione testata]) VALUES (?, ?)",
            row.id, row.locazione
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def export_banchi(mssql_cur, access_cur):
    print("\n📦 shared.banchi → TBanchi")
    try:
        mssql_cur.execute("SELECT id, descrizione FROM shared.banchi")
        rows = mssql_cur.fetchall()
        
        for row in rows:
            access_cur.execute(
                "INSERT INTO TBanchi (ID, Descrizione) VALUES (?, ?)",
                row.id, row.descrizione
            )
        print(f"   ✅ {len(rows)} record")
        return len(rows)
    except:
        print("   ⚠️  Tabella non trovata o vuota")
        return 0


def export_periodi(mssql_cur, access_cur):
    print("\n📦 shared.periodi → TPeriodiSellOut")
    
    mssql_cur.execute("SELECT id, anno, codice, data_inizio, data_fine, num_hostess FROM shared.periodi")
    rows = mssql_cur.fetchall()
    
    for row in rows:
        # Rimuovi prefisso P- dal codice per Access
        codice = row.codice
        if codice and codice.startswith('P-'):
            codice = codice[2:]
        
        access_cur.execute(
            "INSERT INTO TPeriodiSellOut (IDPeriodo, AnnoRif, CodPromo, [Data Inizio], [Data Fine], NHostess) VALUES (?, ?, ?, ?, ?, ?)",
            row.id, row.anno, codice, row.data_inizio, row.data_fine, row.num_hostess
        )
    print(f"   ✅ {len(rows)} record")
    return len(rows)


def export_assegnazioni_pallet(mssql_cur, access_cur):
    print("\n📦 shared.assegnazioni_pallet → TScelte")
    
    mssql_cur.execute("""
        SELECT ap.periodo_id, p.codice as pallet_codice, p.buyer_id, ap.fornitore_id, 
               ap.dettaglio, ap.nota, ap.nota_estesa
        FROM shared.assegnazioni_pallet ap
        JOIN shared.pallet p ON ap.pallet_id = p.id
    """)
    rows = mssql_cur.fetchall()
    
    count = 0
    for row in rows:
        try:
            access_cur.execute(
                "INSERT INTO TScelte (NumPeriodo, Pallet, NumBuyer, Fornitore, Dettaglio, Nota, Nota1) VALUES (?, ?, ?, ?, ?, ?, ?)",
                row.periodo_id, row.pallet_codice, row.buyer_id, row.fornitore_id, 
                row.dettaglio, row.nota, row.nota_estesa
            )
            count += 1
        except Exception as e:
            if count < 5:  # Mostra solo primi 5 errori
                print(f"   ⚠️  Errore: {e}")
    print(f"   ✅ {count} record")
    return count


def export_assegnazioni_testate(mssql_cur, access_cur):
    print("\n📦 shared.assegnazioni_testate → TSceltaTestate")
    
    mssql_cur.execute("""
        SELECT mese, anno, testata_id, fornitore_id, nota_testata, nota_atelier, log
        FROM shared.assegnazioni_testate
    """)
    rows = mssql_cur.fetchall()
    
    count = 0
    for row in rows:
        try:
            access_cur.execute(
                "INSERT INTO TSceltaTestate (CodeMese, Anno, CodeTestata, CodeFornitore, NotaTestata, NotaAtelier, log) VALUES (?, ?, ?, ?, ?, ?, ?)",
                row.mese, row.anno, row.testata_id, row.fornitore_id,
                row.nota_testata, row.nota_atelier, row.log
            )
            count += 1
        except Exception as e:
            if count < 5:
                print(f"   ⚠️  Errore: {e}")
    print(f"   ✅ {count} record")
    return count


def main():
    print("=" * 60)
    print("ESPORTAZIONE MSSQL → ACCESS (ROLLBACK)")
    print("Pallet-Promoter")
    print("=" * 60)
    print(f"Database MSSQL: {MSSQL_DATABASE}")
    print(f"File Access: {ACCESS_FILE}")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print("\n⚠️  ATTENZIONE: Questo sovrascriverà i dati in Access!")
    risposta = input("Continuare? (s/n): ")
    if risposta.lower() != 's':
        print("Operazione annullata.")
        return
    
    # Connessioni
    try:
        mssql_conn = get_mssql_conn()
        mssql_cur = mssql_conn.cursor()
        print("✅ Connesso a MSSQL")
    except Exception as e:
        print(f"❌ Errore connessione MSSQL: {e}")
        return
    
    try:
        access_conn = get_access_conn()
        access_cur = access_conn.cursor()
        print("✅ Connesso a Access")
    except Exception as e:
        print(f"❌ Errore connessione Access: {e}")
        return
    
    # Esportazione - ORDINE IMPORTANTE: prima figlie, poi padri
    total = 0
    
    try:
        # Prima svuoto TUTTE le tabelle figlie
        print("\n🗑️  Svuoto tabelle (livello 1 - assegnazioni)...")
        tabelle_livello1 = ['TScelte', 'TSceltaTestate', 'THostessTask', 'TSceltaHostess']
        for t in tabelle_livello1:
            try:
                access_cur.execute(f"DELETE FROM {t}")
                access_conn.commit()
                print(f"   {t} svuotata")
            except Exception as e:
                pass
        
        print("\n🗑️  Svuoto tabelle (livello 2 - intermedie)...")
        tabelle_livello2 = ['TPallet', 'TTestate', 'TBanchi']
        for t in tabelle_livello2:
            try:
                access_cur.execute(f"DELETE FROM {t}")
                access_conn.commit()
                print(f"   {t} svuotata")
            except Exception as e:
                print(f"   ⚠️  {t}: {e}")
        
        print("\n🗑️  Svuoto tabelle (livello 3 - dipendenti da buyer)...")
        tabelle_livello3 = ['TPwd', 'TPeriodiSellOut']
        for t in tabelle_livello3:
            try:
                access_cur.execute(f"DELETE FROM {t}")
                access_conn.commit()
                print(f"   {t} svuotata")
            except Exception as e:
                print(f"   ⚠️  {t}: {e}")
        
        print("\n🗑️  Svuoto anagrafiche base...")
        tabelle_anag = ['TFornitori', 'THostess', 'TBuyer', 'T_Reparti', 'T_Agenzie']
        for t in tabelle_anag:
            try:
                access_cur.execute(f"DELETE FROM {t}")
                access_conn.commit()
                print(f"   {t} svuotata")
            except Exception as e:
                print(f"   ⚠️  {t}: {e}")
        
        # Ora inserisco tutto nell'ordine corretto
        print("\n📥 Inserimento dati...")
        
        total += export_agenzie(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_reparti(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_buyer(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_hostess(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_fornitori(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_pallet(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_testate(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_banchi(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_periodi(mssql_cur, access_cur)
        access_conn.commit()
        
        # Infine esporto assegnazioni
        total += export_assegnazioni_pallet(mssql_cur, access_cur)
        access_conn.commit()
        
        total += export_assegnazioni_testate(mssql_cur, access_cur)
        access_conn.commit()
        
    except Exception as e:
        print(f"\n❌ Errore durante esportazione: {e}")
        access_conn.rollback()
    
    # Chiudi connessioni
    mssql_conn.close()
    access_conn.close()
    
    print("\n" + "=" * 60)
    print(f"COMPLETATO! Totale record esportati: {total}")
    print("=" * 60)


if __name__ == '__main__':
    main()
