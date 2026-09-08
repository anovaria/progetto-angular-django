import logging
from django.db import connections

logger = logging.getLogger(__name__)


def cerca_ccom(ccom: str) -> dict | None:
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
    """Legge ultima configurazione ordine da goldcursori (cross-db dalla connessione goldreport)."""
    sql = """
        SELECT TOP 1
            ggconsegna, ggCopertura, Alg,
            Ul_Ordine, numord, note, email, email1, email2, email3
        FROM [172.17.10.51].goldcursori.dbo.t_masterfornrio
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
    emails = [e for e in [row[6], row[7], row[8], row[9]] if e and str(e).strip()]
    return {
        'ggconsegna': row[0] or 7,
        'ggcopertura': row[1] or 35,
        'alg': row[2],
        'ul_ordine': row[3],
        'numord': row[4],
        'note': row[5] or '',
        'emails_fornitore': emails,
    }


def aggiorna_email_fornitore(ccom: str, email: str, email1: str, email2: str, email3: str) -> tuple[bool, str]:
    sql = """
        UPDATE [172.17.10.51].goldcursori.dbo.t_masterfornrio
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
                  riduzione_perc: int, dove: str, manda_mail: int) -> tuple[bool, str]:
    perc_sp = 100 - riduzione_perc if tip_ord == 1 else 0
    sql = """
        EXEC [172.17.10.51].Db_GoldReport.dbo.OrdineFornitore_04_dash
            @contrcomme=%s, @ggcons=%s, @ggcop=%s,
            @tipOrd=%s, @perc=%s, @mandaMail=%s, @dove=%s, @email=%s
    """
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql, [ccom, gg_cons, gg_cop, tip_ord, perc_sp, manda_mail, dove, ''])
    except Exception as e:
        logger.exception("esegui_ordine: errore SP ccom=%s", ccom)
        return False, str(e)
    return True, ""
