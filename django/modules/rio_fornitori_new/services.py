"""
services.py - Accesso ai dati per l'app rio_fornitori_new (riordino fornitori su srviisnew).

Tutte le query usano la connessione Django 'goldreport' (Db_GoldReport su srviisnew)
e nomi a 3 parti (es. goldcursori.dbo.t_...), senza il linked server [172.17.10.51]:
questa app lavora direttamente sul nuovo server, mentre l'app di produzione
rio_fornitori continua a puntare al vecchio srviis.
"""
import logging
from django.db import connections

logger = logging.getLogger(__name__)


def cerca_ccom(ccom: str) -> dict | None:
    """
    Cerca un fornitore (contratto commerciale) in t_masterData a partire dal codice.
    Ritorna {'ccom', 'descrccom'} se trovato, altrimenti None.
    """
    sql = "SELECT TOP 1 ccom, descrccom FROM dbo.t_masterData WHERE ccom = %s"
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql, [ccom])
            row = cur.fetchone()
    except Exception:
        logger.exception("cerca_ccom: errore query ccom=%s", ccom)
        return None
    if not row:
        return None
    return {'ccom': str(row[0]).strip(), 'descrccom': str(row[1]).strip()}


def leggi_config_fornitore(ccom: str) -> dict | None:
    """
    Legge i parametri del fornitore da t_masterfornrio (giorni consegna/copertura,
    algoritmo, ultimo ordine, note ed email per la notifica).
    Ritorna un dict con i campi utili alla schermata, oppure None se il fornitore
    non e' presente in tabella.
    """
    sql = """
        SELECT TOP 1
            ggconsegna, ggCopertura, Alg,
            Ul_Ordine, numord, note, email, email1, email2, email3, DESCRCCOM
        FROM goldcursori.dbo.t_masterfornrio
        WHERE CCOM = %s
    """
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql, [ccom])
            row = cur.fetchone()
    except Exception:
        logger.exception("leggi_config_fornitore: errore query ccom=%s", ccom)
        return None
    if not row:
        return None
    # Raccoglie le 4 email scartando quelle vuote.
    emails = [e for e in [row[6], row[7], row[8], row[9]] if e and str(e).strip()]
    return {
        # Valori di default (7 e 35) se i campi sono nulli in tabella.
        'ggconsegna': row[0] or 7,
        'ggcopertura': row[1] or 35,
        'alg': row[2],
        'ul_ordine': row[3],
        'numord': row[4],
        'note': row[5] or '',
        'emails_fornitore': emails,
        'descrccom': str(row[10]).strip() if row[10] else '',
    }


def aggiorna_email_fornitore(ccom: str, email: str, email1: str, email2: str, email3: str) -> tuple[bool, str]:
    """
    Aggiorna le 4 email del fornitore in t_masterfornrio.
    Le stringhe vuote vengono salvate come NULL. Ritorna (ok, errore).
    """
    sql = """
        UPDATE goldcursori.dbo.t_masterfornrio
        SET email=%s, email1=%s, email2=%s, email3=%s
        WHERE CCOM=%s
    """
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql, [email or None, email1 or None, email2 or None, email3 or None, ccom])
    except Exception as e:
        logger.exception("aggiorna_email_fornitore: errore ccom=%s", ccom)
        return False, str(e)
    return True, ""


def esegui_ordine(ccom: str, gg_cons: int, gg_cop: int, tip_ord: int,
                  riduzione_perc: int) -> tuple[bool, str, str | None]:
    """
    Lancia il calcolo della proposta d'ordine chiamando la SP OrdineFornitore_Dash
    con @skipExe=1.

    Con @skipExe=1 la SP NON genera il CSV con bcp e NON lancia il vecchio exe:
    si limita a popolare la tabella di appoggio t_exportfoRiodash e a registrare il
    file in t_fileRiodash, restituendo il numero ordine tramite il parametro OUTPUT
    @nrOrd. Il trasferimento vero e proprio (CSV/SFTP/Oracle/SSH) lo fa poi il modulo
    transfer.trasferisci_proposta().

    @perc passato alla SP: se tip_ord==1 si invia (100 - riduzione%), altrimenti 0.

    Ritorna (ok, errore, nr_ord):
      - ok=True, errore='', nr_ord=<numero ordine> se la SP e' andata a buon fine;
      - ok=False, errore=<descrizione>, nr_ord=None in caso di eccezione SQL.
    """
    perc_sp = 100 - riduzione_perc if tip_ord == 1 else 0

    # Batch T-SQL: dichiara una variabile, esegue la SP passandola come OUTPUT,
    # poi la "rilegge" con una SELECT finale. E' il modo affidabile per recuperare
    # un parametro OUTPUT tramite pyodbc.
    #
    # LOCK APPLICATIVO: la SP usa tabelle scratch CONDIVISE (Db_goldreport..Masterd,
    # ..t_Ord902) che ricrea a ogni run con DROP + SELECT INTO. Due ordini lanciati
    # insieme (utenti diversi, oppure un doppio invio) collidono sul SELECT INTO ->
    # errore 2714 "There is already an object named 'Masterd'". sp_getapplock
    # serializza l'esecuzione: il secondo run ATTENDE (fino a @LockTimeout) invece di
    # fallire. La risorsa e' rilasciata sia sul percorso normale sia in CATCH (e
    # quindi mai lasciata appesa su una connessione poolata), poi si rilancia
    # l'errore originale perche' Python lo gestisca come prima.
    sql = """
        DECLARE @out varchar(13), @rc int;
        EXEC @rc = sp_getapplock @Resource='rio_ordine_fornitore_dash',
            @LockMode='Exclusive', @LockOwner='Session', @LockTimeout=30000;
        IF @rc < 0
            THROW 50001, 'Un altro ordine e'' in corso, riprovare tra qualche secondo.', 1;
        BEGIN TRY
            EXEC Db_GoldReport.dbo.OrdineFornitore_Dash
                @contrcomme=%s, @ggcons=%s, @ggcop=%s,
                @tipOrd=%s, @perc=%s, @skipExe=1, @nrOrd=@out OUTPUT;
        END TRY
        BEGIN CATCH
            EXEC sp_releaseapplock @Resource='rio_ordine_fornitore_dash', @LockOwner='Session';
            THROW;
        END CATCH;
        EXEC sp_releaseapplock @Resource='rio_ordine_fornitore_dash', @LockOwner='Session';
        SELECT @out AS nrord;
    """
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql, [ccom, gg_cons, gg_cop, tip_ord, perc_sp])
            # La SP puo' emettere piu' result set: scorriamo tutti i set e teniamo
            # l'ultimo valore non nullo, che corrisponde alla SELECT @out finale.
            nr_ord = None
            while True:
                if cur.description:
                    row = cur.fetchone()
                    if row and row[0]:
                        nr_ord = str(row[0]).strip()
                if not cur.nextset():
                    break
    except Exception as e:
        # Qui rientra anche il caso "fornitore non trovato" (la SP fa RAISERROR).
        logger.exception("esegui_ordine: errore SP ccom=%s", ccom)
        return False, str(e), None
    return True, "", nr_ord


def conta_ordini_aperti(ccom: str) -> tuple[bool, int, str]:
    """
    Conta gli ordini APERTI su Gold (Oracle GOLDPROD) per il contratto <ccom>: testate
    cdeentcde in stato ECDETAT='5' (in attesa di ricevimento) con data ordine ECDDCOM
    tra sysdate-30 e sysdate+10.

    Replica la "guardia" del task legacy di Onesti Group, che NON riordina se c'e' gia'
    un ordine in corso per il fornitore: quel task gira OGNI GIORNO e senza la guardia
    accumulerebbe ordini doppi finche' il precedente non viene ricevuto.

    La conta gira via openquery sul linked server GOLDPROD (lo stesso usato dalla SP di
    riordino e da sp_Create_t_OrdiniGenerale). Dentro openquery il parametro non e'
    passabile come bind, quindi <ccom> viene VALIDATO come numerico e concatenato nella
    stringa Oracle (evita ogni iniezione).

    Ritorna (ok, n_aperti, errore):
      - ok=True,  n_aperti>=0, errore=''         -> conta riuscita;
      - ok=False, n_aperti=0,  errore=<descr>    -> conta fallita: il chiamante NON deve
        procedere alla cieca ne' saltare in silenzio, ma segnalarlo (meglio un ordine in
        meno con avviso che un doppione o un salto muto).
    """
    if not str(ccom).isdigit():
        return False, 0, "CCOM non numerico: %r" % ccom

    # Stringa Oracle come literal dentro openquery: gli apici Oracle vanno RADDOPPIATI.
    oracle = (
        "select count(*) c from cdeentcde "
        "where ECDETAT in (''5'') "
        "and ECDDCOM between trunc(sysdate-30) and trunc(sysdate+10) "
        "and PKFOUCCOM.GET_NUMCONTRAT(0,ECDCCIN) = ''%s''" % ccom
    )
    sql = "SELECT c FROM openquery(GOLDPROD, '%s')" % oracle
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            n = int(row[0]) if row and row[0] is not None else 0
    except Exception as e:
        logger.exception("conta_ordini_aperti: errore ccom=%s", ccom)
        return False, 0, str(e)
    return True, n, ""
