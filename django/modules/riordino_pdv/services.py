"""
services.py — accesso dati per Riordino PDV (Parametri Rio).

Pagina di amministrazione del portale (NON palmare) che visualizza la
schedulazione del riordino automatico PDV. Per ora SOLA LETTURA.

Legge t_corsiaabilita1 su GoldCursori srviis (172.17.10.51) via linked server
dalla connessione 'goldreport' (stesso pattern di modules/rio_fornitori).
"""
import logging
from django.db import connections

logger = logging.getLogger(__name__)

_POS_DB = '[172.17.10.51].goldcursori.dbo'   # GoldCursori su srviis via linked server


def schedule() -> list[dict]:
    """
    Schedulazione settimanale del riordino (porting in lettura della griglia di
    P_rio.aspx): legge t_corsiaabilita1 (righe con descrizione note3).
    Una riga per corsia/fascia, con i 7 giorni come booleani.
    """
    sql = f"""
        SELECT Corsia,
               note3 AS Descrizione,
               CASE WHEN note = 'Ordine3'   THEN 'Min --> Max'
                    WHEN note = 'OrdineMax'  THEN 'Max' END AS Tipo_Ordine,
               note1 AS Abilitata,
               note2 AS Lato,
               CASE WHEN matt_pom = 'M' THEN 'Mattino'
                    WHEN matt_pom = 'P' THEN 'Pome' END AS Matt_Pom,
               Lun, Mar, Mer, Gio, Ven, Sab, Dom
        FROM {_POS_DB}.t_corsiaabilita1
        WHERE note3 IS NOT NULL
        ORDER BY CONVERT(int, Corsia), matt_pom ASC
    """
    out: list[dict] = []
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql)
            for r in cur.fetchall():
                out.append({
                    'corsia':      str(r[0] or '').strip(),
                    'descrizione': str(r[1] or '').strip(),
                    'tipo_ordine': str(r[2] or '').strip(),
                    'abilitata':   str(r[3] or '').strip(),
                    'lato':        str(r[4] or '').strip(),
                    'matt_pom':    str(r[5] or '').strip(),
                    'giorni': {
                        'Lun': bool(r[6]),  'Mar': bool(r[7]),  'Mer': bool(r[8]),
                        'Gio': bool(r[9]),  'Ven': bool(r[10]), 'Sab': bool(r[11]),
                        'Dom': bool(r[12]),
                    },
                })
    except Exception:
        logger.exception("riordino_pdv.schedule: errore lettura t_corsiaabilita1")
    return out
