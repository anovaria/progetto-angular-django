"""
transfer.py - Trasferimento della proposta d'ordine alla Dashboard Gold, in puro Python.

SCOPO
-----
Questo modulo sostituisce il vecchio eseguibile trasffilerioDash.exe (che veniva
lanciato da SQL Server tramite xp_cmdshell) replicandone gli stessi 4 passi, ma
direttamente dal portale e con le credenziali prese dai settings (non piu'
hardcoded in un binario):

  1. CSV     -> legge le righe della proposta da goldcursori.dbo.t_exportfoRiodash
                e costruisce il file CSV in memoria (stesso formato del vecchio bcp:
                riga di intestazione + righe dati, separatore ';', valori "trimmati").
  2. SFTP    -> carica il CSV sul server Gold (con paramiko, al posto di WinSCP).
  3. ORACLE  -> chiama la stored procedure Oracle sil_rioDash su GOLDPROD, che importa
                il file appena caricato (con oracledb in "thin mode", al posto di ODP.NET).
  4. SSH     -> esegue sul server Gold lo script gc_xls_xlsord.sh (con paramiko, al
                posto di Renci.SshNet).

Alla fine aggiorna lo stato del file in goldcursori.dbo.t_fileRiodash
(elab/EsitoImport) e svuota la tabella di appoggio t_exportfoRiodash.

CONFIGURAZIONE
--------------
Endpoint e credenziali stanno nei settings come variabili RIO_DASH_* (vedi base.py),
a loro volta lette da variabili d'ambiente (impostate in NSSM in test/prod).

MODALITA' DRY RUN
-----------------
Se il setting RIO_DASH_DRY_RUN e' attivo (default), il modulo genera e salva il CSV
ma NON esegue SFTP/Oracle/SSH e NON modifica lo stato sul DB: serve per collaudare
la generazione del file senza toccare Gold.

NOTA SUGLI IMPORT
-----------------
paramiko e oracledb sono importati "lazy" (dentro le funzioni che li usano) e non in
cima al modulo: cosi' un eventuale venv privo di quei pacchetti non impedisce il
caricamento dell'intero portale: a fallire e' solo l'esecuzione del trasferimento,
con un messaggio chiaro.
"""
import io
import logging

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)

# Messaggio restituito quando la SP ha creato l'ordine ma la proposta e' vuota
# (0 righe in t_exportfoRiodash): NON e' un errore di trasferimento, e' "nessun
# articolo da ordinare". Esposto come costante cosi' i chiamanti (es. rio_auto)
# possono distinguerlo da un fallimento vero senza confrontare stringhe magiche.
MSG_PROPOSTA_VUOTA = "Nessun articolo da ordinare (proposta vuota)."

# Colonne esportate, NELL'ORDINE atteso dal loader Oracle.
# E' lo stesso elenco/ordine dell'intestazione che generava il vecchio bcp.
EXPORT_COLUMNS = [
    'numord', 'riferimento', 'fornitore', 'filiera', 'contrattoCommerciale',
    'codarticolo', 'vl', 'sito', 'dtaordine', 'dtaConsegna', 'qta',
    'uAcq', 'prezzoVendita', 'ivaacquisto', 'valuta', 'statoOrdine',
]

# Query che estrae le righe della proposta dalla tabella di appoggio.
# DISTINCT + TRIM replicano esattamente il "select distinct" con trim() del vecchio bcp,
# cosi' il CSV prodotto e' identico a quello che generava la SP.
_SELECT_EXPORT = """
    SELECT DISTINCT
        TRIM(numord), TRIM(riferimento), TRIM(fornitore),
        TRIM(filiera), contrattoCommerciale, TRIM(codarticolo), TRIM(vl),
        TRIM(sito), TRIM(dtaordine), TRIM(dtaConsegna), TRIM(qta),
        TRIM(uAcq), TRIM(prezzoVendita), TRIM(ivaacquisto),
        TRIM(valuta), TRIM(statoOrdine)
    FROM goldcursori.dbo.t_exportfoRiodash
"""

# --- Canale CENTRAL (7 fornitori automatici legacy: @dove='Central') -------
# Colonne/query per goldcursori.dbo.t_exportfoRio, popolata da
# services.costruisci_export_central(). Stesso elenco/ordine del vecchio bcp
# del ramo Central della SP legacy OrdineFornitore_04_dash.
EXPORT_COLUMNS_CENTRAL = [
    'numOrdine', 'prRiga', 'cnuf', 'filiera', 'ccom', 'codart', 'Vl', 'sito',
    'dataord', 'datacons', 'qta', 'mis', 'listino', 'iva', '978', 'statordine',
]

_SELECT_EXPORT_CENTRAL = """
    SELECT DISTINCT
        numord, numrig, numfo, c, ccom, codart, vl, sito,
        dt_ord, dt_cons, qta, gest, przacq, iva, a978, stato
    FROM goldcursori.dbo.t_exportfoRio
    WHERE numord = %s
"""


class TransferError(Exception):
    """Errore in una delle fasi di trasferimento verso Gold (configurazione mancante, ecc.)."""


def _cfg(name, default=None):
    """Scorciatoia per leggere un setting RIO_DASH_* con un valore di default."""
    return getattr(settings, name, default)


def _build_csv():
    """
    Legge t_exportfoRiodash e costruisce il contenuto del CSV.

    Ritorna una tupla (csv_bytes, rows):
      - csv_bytes: il file gia' codificato, pronto da inviare/salvare;
      - rows: la lista delle righe dati (tuple nell'ordine di EXPORT_COLUMNS), usata
              sia per contarle sia per mostrare l'anteprima della proposta all'utente.

    Formato: prima riga di intestazione con i nomi colonna, poi una riga per articolo;
    campi separati da RIO_DASH_CSV_SEP, fine riga RIO_DASH_CSV_NEWLINE, codifica
    RIO_DASH_CSV_ENCODING. I valori None diventano stringa vuota.
    """
    sep = _cfg('RIO_DASH_CSV_SEP', ';')
    newline = _cfg('RIO_DASH_CSV_NEWLINE', '\r\n')
    encoding = _cfg('RIO_DASH_CSV_ENCODING', 'utf-8')

    # Estrae le righe della proposta dalla tabella di appoggio su srviisnew.
    with connections['goldreport'].cursor() as cur:
        cur.execute(_SELECT_EXPORT)
        rows = cur.fetchall()

    # Prima riga: intestazione con i nomi delle colonne.
    lines = [sep.join(EXPORT_COLUMNS)]
    # Righe dati: ogni valore None -> '', gli altri convertiti a stringa e ripuliti.
    for row in rows:
        lines.append(sep.join('' if v is None else str(v).strip() for v in row))

    # Unisce tutto con il terminatore di riga e aggiunge una newline finale.
    text = newline.join(lines) + newline
    return text.encode(encoding), rows


def _sftp_upload(csv_bytes, remote_filename):
    """
    Carica via SFTP il contenuto CSV sul server Gold (passo 2).
    Sostituisce la parte WinSCP del vecchio exe.
    """
    import paramiko  # import lazy: vedi nota in cima al modulo

    host = _cfg('RIO_DASH_SFTP_HOST', '172.17.10.41')
    port = int(_cfg('RIO_DASH_SFTP_PORT', 22))
    user = _cfg('RIO_DASH_SFTP_USER', 'glpcenadm')
    password = _cfg('RIO_DASH_SFTP_PASS', '')
    dest_dir = _cfg('RIO_DASH_SFTP_DEST', '/gold/glp/central/gaia/RECEIVED/')

    # La password DEVE arrivare dall'ambiente (NSSM): se manca, fermati subito.
    if not password:
        raise TransferError("RIO_DASH_SFTP_PASS non configurata (variabile d'ambiente).")

    # Percorso remoto completo: cartella di destinazione + nome file.
    remote_path = dest_dir.rstrip('/') + '/' + remote_filename

    transport = paramiko.Transport((host, port))
    try:
        transport.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        # putfo invia direttamente i byte in memoria, senza creare un file temporaneo.
        sftp.putfo(io.BytesIO(csv_bytes), remote_path)
        logger.info("SFTP ok: %s (%d byte) -> %s", remote_filename, len(csv_bytes), remote_path)
    finally:
        # Chiude sempre la connessione, anche in caso di errore.
        transport.close()


def _oracle_sil_riodash(nomefile):
    """
    Chiama la stored procedure Oracle sil_rioDash su GOLDPROD (passo 3).
    Sostituisce la parte ODP.NET del vecchio exe.

    Firma reale della SP: sil_rioDash(NomeFile IN VARCHAR2, Stato OUT NUMBER,
    P_F_ERR OUT VARCHAR2).

    ATTENZIONE all'interpretazione dei parametri di uscita:
      - Stato: indicatore numerico di esito. Dai sorgenti della SP:
            0 = file non trovato (ERRORE1)
            1 = errore in fase 1 (ERRORE2)
            2 = caricamento ok (e' il valore del percorso "buono" reale: la SP,
                per come e' scritta, esce dall'handler ERRORE3 con Stato=2)
            3 = previsto come "tutto importato", di fatto non raggiunto dal codice
      - P_F_ERR: NON e' un flag d'errore. La SP lo valorizza ANCHE sui successi
            (es. 'FASE 1: COMPLETATA...', 'FASE 2: COMPLETATA...'), quindi va usato
            solo come messaggio diagnostico da loggare, mai per decidere l'esito.

    Inoltre la SP intercetta internamente tutte le eccezioni (named + WHEN OTHERS
    con ROLLBACK) e non le ripropaga: a oracledb arriva un errore solo per problemi
    di connessione/protocollo. Per questo - come faceva il vecchio exe - l'esito si
    giudica sull'assenza di eccezione, usando Stato solo per intercettare i fallimenti
    inequivocabili (0/1).

    Ritorna la tupla (stato, messaggio):
      - stato: intero restituito dalla SP, oppure None se non valorizzato;
      - messaggio: il testo di P_F_ERR (diagnostico).
    """
    import oracledb  # import lazy: vedi nota in cima al modulo

    dsn = _cfg('RIO_DASH_ORACLE_DSN', 'Srvoracle.groscidac.local:1521/GOLDPROD')
    user = _cfg('RIO_DASH_ORACLE_USER', 'GOLDCEN')
    password = _cfg('RIO_DASH_ORACLE_PASS', '')
    proc = _cfg('RIO_DASH_ORACLE_PROC', 'sil_rioDash')

    # Anche qui la password deve arrivare dall'ambiente (NSSM).
    if not password:
        raise TransferError("RIO_DASH_ORACLE_PASS non configurata (variabile d'ambiente).")

    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    try:
        cur = conn.cursor()
        # Stato e' OUT NUMBER nella SP; P_F_ERR e' OUT VARCHAR2 (messaggio diagnostico).
        stato = cur.var(oracledb.NUMBER)
        ferr = cur.var(oracledb.STRING)
        cur.callproc(proc, [nomefile, stato, ferr])
        conn.commit()
        sv = stato.getvalue()
        return (int(sv) if sv is not None else None), (ferr.getvalue() or '')
    finally:
        conn.close()


def _build_csv_central(nr_ord):
    """
    Legge t_exportfoRio (righe del canale Central, filtrate su nr_ord appena
    inserito da services.costruisci_export_central) e costruisce il CSV nello
    stesso formato del vecchio bcp del ramo @dove='Central'.

    Ritorna (csv_bytes, rows), stesso significato di _build_csv.
    """
    sep = _cfg('RIO_DASH_CSV_SEP', ';')
    newline = _cfg('RIO_DASH_CSV_NEWLINE', '\r\n')
    encoding = _cfg('RIO_DASH_CSV_ENCODING', 'utf-8')

    with connections['goldreport'].cursor() as cur:
        cur.execute(_SELECT_EXPORT_CENTRAL, [nr_ord])
        rows = cur.fetchall()

    lines = [sep.join(EXPORT_COLUMNS_CENTRAL)]
    for row in rows:
        lines.append(sep.join('' if v is None else str(v).strip() for v in row))

    text = newline.join(lines) + newline
    return text.encode(encoding), rows


def _oracle_sil_rio(nomefile):
    """
    Chiama la stored procedure Oracle SIL_Rio su GOLDPROD (canale Central).
    Sostituisce la parte ODP.NET del vecchio trasffilerio.exe (lo stesso exe
    usato da RIOQ10).

    Firma reale (letta dal sorgente PL/SQL): SIL_Rio(NomeFile IN VARCHAR2,
    Stato OUT NUMBER, P_F_ERR OUT VARCHAR2).

    A differenza di sil_rioDash, SIL_Rio fa Fase 1 E Fase 2 nella STESSA
    chiamata (TSK_XLSORD.TSP_GESFLU poi, se FaseImport=2, TSK_XLSORD.TSP_ELAFLU
    con COMMIT): l'ordine reale in CDEENTCDE/CDEDETCDE viene scritto qui, non
    da uno script SSH successivo.
        Stato = -1  timeout (coda occupata da un altro file, riprovare)
               =  0  errore inizializzazione (ERRORE1)
               =  1  errore Fase 1 (ERRORE2)
               =  2  errore Fase 2 (ERRORE3): Fase 1 ok, Fase 2 fallita
               =  3  Fase 2 completata: ordine reale creato (successo pieno)
    P_F_ERR e' diagnostico (valorizzato anche nei rami di successo), mai da
    usare per decidere l'esito.

    Ritorna la tupla (stato, messaggio).
    """
    import oracledb  # import lazy: vedi nota in cima al modulo

    dsn = _cfg('RIO_CENTRAL_ORACLE_DSN', _cfg('RIO_DASH_ORACLE_DSN'))
    user = _cfg('RIO_CENTRAL_ORACLE_USER', _cfg('RIO_DASH_ORACLE_USER'))
    password = _cfg('RIO_CENTRAL_ORACLE_PASS', _cfg('RIO_DASH_ORACLE_PASS'))
    proc = _cfg('RIO_CENTRAL_ORACLE_PROC', 'SIL_Rio')

    if not password:
        raise TransferError("RIO_CENTRAL_ORACLE_PASS/RIO_DASH_ORACLE_PASS non configurata.")

    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    try:
        cur = conn.cursor()
        stato = cur.var(oracledb.NUMBER)
        ferr = cur.var(oracledb.STRING)
        cur.callproc(proc, [nomefile, stato, ferr])
        conn.commit()
        sv = stato.getvalue()
        return (int(sv) if sv is not None else None), (ferr.getvalue() or '')
    finally:
        conn.close()


def _update_stato_central(nomefile, elab, esito):
    """Aggiorna lo stato del file nella tabella di tracciamento t_fileRio (canale Central)."""
    sql = """
        UPDATE goldcursori.dbo.t_fileRio
        SET elab=%s, EsitoImport=%s
        WHERE NomeFile=%s
    """
    with connections['goldreport'].cursor() as cur:
        cur.execute(sql, [elab, esito, nomefile])


def _safe_update_central(nomefile, elab, esito):
    try:
        _update_stato_central(nomefile, elab, esito)
    except Exception:
        logger.exception("Impossibile aggiornare t_fileRio per %s", nomefile)


def trasferisci_proposta_central(nr_ord, dry_run=None):
    """
    Trasferisce a Gold, canale CENTRAL, la proposta gia' costruita da
    services.costruisci_export_central() in t_exportfoRio/t_fileRio (che a sua
    volta riusa il calcolo gia' fatto da OrdineFornitore_Dash in
    t_exportfoRiodash: nessuna riscrittura della logica di calcolo).

    Sequenza: genera CSV -> (dry-run si ferma qui) -> SFTP -> Oracle SIL_Rio
    (Fase 1+2 nella stessa chiamata, niente SSH separato) -> aggiorna stato in
    t_fileRio.

    Ritorna (ok, messaggio, csv_bytes, rows), stesso significato di
    trasferisci_proposta.
    """
    nomefile = "%s.csv" % nr_ord

    try:
        csv_bytes, rows = _build_csv_central(nr_ord)
    except Exception as e:
        logger.exception("trasferisci_proposta_central: errore generazione CSV %s", nomefile)
        return False, "Errore generazione CSV: %s" % e, None, None

    n_righe = len(rows)
    if n_righe == 0:
        logger.info("trasferisci_proposta_central: nessuna riga in t_exportfoRio per %s", nomefile)
        return False, MSG_PROPOSTA_VUOTA, None, None

    _save_output(nomefile, csv_bytes)

    if dry_run is None:
        dry_run = _cfg('RIO_AUTO_DRY_RUN', True)
    if dry_run:
        encoding = _cfg('RIO_DASH_CSV_ENCODING', 'utf-8')
        preview = csv_bytes.decode(encoding, errors='replace').splitlines()[:10]
        logger.info("DRY RUN %s: %d righe\nAnteprima:\n%s", nomefile, n_righe, "\n".join(preview))
        return True, ("DRY RUN: CSV generato (%d righe). "
                      "Nessun invio a Gold (SFTP/Oracle saltati)." % n_righe), csv_bytes, rows

    try:
        _sftp_upload(csv_bytes, nomefile)
    except Exception as e:
        logger.exception("trasferisci_proposta_central: SFTP fallito %s", nomefile)
        _safe_update_central(nomefile, '-1', 'No')
        return False, "Trasferimento SFTP fallito: %s" % e, csv_bytes, rows

    try:
        stato, msg = _oracle_sil_rio(nomefile)
        logger.info("SIL_Rio %s: Stato=%s, P_F_ERR=%s", nomefile, stato, msg)
        if stato != 3:
            logger.error("SIL_Rio: import non completato %s (Stato=%s): %s", nomefile, stato, msg)
            _safe_update_central(nomefile, '-1', 'No')
            return False, ("Import Oracle non completato (Stato=%s): %s" % (stato, (msg or '').strip())), csv_bytes, rows
    except Exception as e:
        logger.exception("trasferisci_proposta_central: SIL_Rio fallito %s", nomefile)
        _safe_update_central(nomefile, '-1', 'No')
        return False, "Chiamata Oracle fallita: %s" % e, csv_bytes, rows

    _safe_update_central(nomefile, '2', 'Ok')

    return True, "Ordine %s creato in Gold (%d righe)." % (nr_ord, n_righe), csv_bytes, rows


def _ssh_run_import():
    """
    Esegue via SSH lo script di import finale sul server Gold (passo 4).
    Sostituisce la parte Renci.SshNet del vecchio exe.
    """
    import paramiko  # import lazy: vedi nota in cima al modulo

    host = _cfg('RIO_DASH_SFTP_HOST', '172.17.10.41')
    port = int(_cfg('RIO_DASH_SFTP_PORT', 22))
    user = _cfg('RIO_DASH_SFTP_USER', 'glpcenadm')
    password = _cfg('RIO_DASH_SFTP_PASS', '')
    cmd = _cfg('RIO_DASH_SSH_CMD', '/gold/glp/central/shell/./gc_xls_xlsord.sh')

    ssh = paramiko.SSHClient()
    # AutoAddPolicy: accetta la chiave host del server senza richiederla prima.
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port=port, username=user, password=password, timeout=30)
        _, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        # Lo stderr non e' necessariamente un errore bloccante: lo logghiamo come warning.
        if err.strip():
            logger.warning("SSH stderr (%s): %s", cmd, err.strip())
        logger.info("SSH ok: %s", cmd)
        return out
    finally:
        ssh.close()


def _update_stato(nomefile, elab, esito):
    """
    Aggiorna lo stato del file nella tabella di tracciamento t_fileRiodash.
      elab  = '2' -> trasferito e importato con successo
            = '-1'-> errore in una delle fasi
      esito = 'Ok' / 'No'
    """
    sql = """
        UPDATE goldcursori.dbo.t_fileRiodash
        SET elab=%s, EsitoImport=%s
        WHERE NomeFile=%s
    """
    with connections['goldreport'].cursor() as cur:
        cur.execute(sql, [elab, esito, nomefile])


def trasferisci_proposta(nr_ord, dry_run=None):
    """
    Esegue l'intero trasferimento per la proposta nr_ord (es. 'DSH2606030001').

    Sequenza: genera CSV -> (in dry-run si ferma qui) -> SFTP -> Oracle -> SSH ->
    aggiorna stato. La tabella di appoggio t_exportfoRiodash non va svuotata qui:
    la SP la tronca all'inizio del run successivo.

    Ritorna la tupla (ok, messaggio, csv_bytes, rows):
      - ok = True  con messaggio descrittivo se tutto e' andato a buon fine;
      - ok = False con messaggio d'errore alla prima fase fallita (e in quel caso
        marca il file con elab='-1'/'No');
      - csv_bytes/rows: il file generato e le sue righe (per anteprima/download),
        valorizzati appena il CSV e' costruito; None se non si e' arrivati a generarlo.

    dry_run: se None (default) vale il setting globale RIO_DASH_DRY_RUN (comportamento
    del flusso manuale); se True/False forza la modalita'. Lo usa il riordino
    automatico (management command rio_auto), che ha un proprio interruttore
    RIO_AUTO_DRY_RUN indipendente da quello del manuale.
    """
    # Il nome file segue la convenzione storica: <numero ordine>.csv
    nomefile = "%s.csv" % nr_ord

    # --- Generazione del CSV (comune a dry-run e trasferimento reale) ---
    try:
        csv_bytes, rows = _build_csv()
    except Exception as e:
        logger.exception("trasferisci_proposta: errore generazione CSV %s", nomefile)
        return False, "Errore generazione CSV: %s" % e, None, None

    n_righe = len(rows)

    # Nessuna riga = nessun articolo da ordinare: non c'e' niente da inviare.
    if n_righe == 0:
        logger.info("trasferisci_proposta: nessuna riga in t_exportfoRiodash per %s", nomefile)
        return False, MSG_PROPOSTA_VUOTA, None, None

    # Salva SEMPRE una copia locale del CSV generato (dry-run e reale): la tabella
    # t_exportfoRiodash viene svuotata al run successivo, quindi il file va conservato
    # ora per permettere all'utente di rivederlo/scaricarlo dalla schermata di esito.
    _save_output(nomefile, csv_bytes)

    # --- DRY RUN: si ferma qui, senza toccare Gold ne' lo stato sul DB ---
    # Un dry_run esplicito (passato dal riordino automatico) ha la precedenza; se None
    # si ricade sul setting globale RIO_DASH_DRY_RUN (comportamento del flusso manuale).
    if dry_run is None:
        dry_run = _cfg('RIO_DASH_DRY_RUN', True)
    if dry_run:
        encoding = _cfg('RIO_DASH_CSV_ENCODING', 'utf-8')
        # Logga le prime 10 righe per un controllo rapido del formato.
        preview = csv_bytes.decode(encoding, errors='replace').splitlines()[:10]
        logger.info("DRY RUN %s: %d righe\nAnteprima:\n%s", nomefile, n_righe, "\n".join(preview))
        return True, ("DRY RUN: CSV generato (%d righe). "
                      "Nessun invio alla Dashboard (SFTP/Oracle/SSH saltati)." % n_righe), csv_bytes, rows

    # --- Passo 1: SFTP del CSV verso Gold ---
    try:
        _sftp_upload(csv_bytes, nomefile)
    except Exception as e:
        logger.exception("trasferisci_proposta: SFTP fallito %s", nomefile)
        _safe_update(nomefile, '-1', 'No')
        return False, "Trasferimento SFTP fallito: %s" % e, csv_bytes, rows

    # --- Passo 2: import lato Oracle (sil_rioDash) ---
    # L'esito si giudica come faceva il vecchio exe: riuscito se la chiamata non
    # solleva eccezione. Stato serve solo a intercettare i fallimenti inequivocabili
    # (0=file non trovato, 1=errore fase 1); P_F_ERR e' diagnostico (valorizzato anche
    # sui successi, es. 'FASE 2: COMPLETATA...') e quindi NON decide l'esito: si logga.
    # Vedi la docstring di _oracle_sil_riodash per i dettagli sui valori di Stato.
    try:
        stato, msg = _oracle_sil_riodash(nomefile)
        logger.info("sil_rioDash %s: Stato=%s, P_F_ERR=%s", nomefile, stato, msg)
        if stato in (0, 1):
            logger.error("sil_rioDash: import fallito %s (Stato=%s): %s", nomefile, stato, msg)
            _safe_update(nomefile, '-1', 'No')
            return False, ("Import Oracle fallito (Stato=%s): %s" % (stato, (msg or '').strip())), csv_bytes, rows
    except Exception as e:
        logger.exception("trasferisci_proposta: sil_rioDash fallito %s", nomefile)
        _safe_update(nomefile, '-1', 'No')
        return False, "Chiamata Oracle fallita: %s" % e, csv_bytes, rows

    # --- Passo 3: esecuzione dello script di import finale via SSH ---
    try:
        _ssh_run_import()
    except Exception as e:
        logger.exception("trasferisci_proposta: SSH fallito %s", nomefile)
        _safe_update(nomefile, '-1', 'No')
        return False, "Esecuzione script Gold fallita: %s" % e, csv_bytes, rows

    # --- Esito positivo: marca il file come elaborato ---
    # Non svuotiamo qui t_exportfoRiodash: la SP OrdineFornitore_Dash fa gia' una
    # truncate difensiva PRIMA della INSERT (07-*.sql), quindi il run successivo
    # parte sempre da tabella pulita. Evita di richiedere ad django_user il diritto
    # ALTER su quella tabella (vedi 10-grant-rio_fornitori_new.sql).
    _safe_update(nomefile, '2', 'Ok')

    return True, "Proposta %s inviata alla Dashboard (%d righe)." % (nr_ord, n_righe), csv_bytes, rows


def _safe_update(nomefile, elab, esito):
    """
    Aggiorna lo stato del file ignorando eventuali errori di scrittura: serve quando
    siamo gia' in un ramo d'errore e non vogliamo mascherare l'errore originale.
    """
    try:
        _update_stato(nomefile, elab, esito)
    except Exception:
        logger.exception("Impossibile aggiornare t_fileRiodash per %s", nomefile)


def _save_output(nomefile, csv_bytes):
    """
    Salva una copia locale del CSV generato nella cartella RIO_DASH_DRY_RUN_DIR, col
    nome <nomefile> (es. DSH2607010001.csv). Serve a dare all'utente la possibilita' di
    rivedere/scaricare il file dalla schermata di esito (vedi views.scarica_csv), dato
    che t_exportfoRiodash viene svuotata al run successivo. Vale in dry-run e in reale.
    Ritorna il percorso salvato, oppure '' se il salvataggio fallisce.
    """
    import os
    d = _cfg('RIO_DASH_DRY_RUN_DIR', '')
    try:
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, nomefile)
        with open(path, 'wb') as f:
            f.write(csv_bytes)
        return path
    except Exception:
        logger.exception("Impossibile salvare la copia CSV per %s", nomefile)
        return ''


def leggi_csv_salvato(nr_ord):
    """
    Rilegge dal disco la copia CSV salvata da _save_output per nr_ord.
    Ritorna i byte del file, oppure None se non presente/leggibile.
    Usata dalla vista di download (views.scarica_csv).
    """
    import os
    d = _cfg('RIO_DASH_DRY_RUN_DIR', '')
    try:
        with open(os.path.join(d, "%s.csv" % nr_ord), 'rb') as f:
            return f.read()
    except Exception:
        return None
