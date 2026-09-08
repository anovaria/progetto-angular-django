"""
services.py — accesso dati per Riordino PDV (Parametri Rio).

Tutte le query operano su GoldCursori srviisnew locale.

GRANT richiesti su GoldCursori (srviisnew) per django_user:
  GRANT SELECT ON dbo.t_corsiaabilita   TO django_user;
  GRANT UPDATE  ON dbo.t_corsiaabilita  TO django_user;
GRANT richiesti su msdb (srviisnew):
  EXEC sp_addrolemember 'SQLAgentOperatorRole', 'django_user';
"""
import datetime
import logging

from django.db import connections

logger = logging.getLogger(__name__)

_JOB = 'Riordino PDV'


def schedule() -> list[dict]:
    """Schedulazione settimanale (griglia read-only, da t_corsiaabilita1 su srviisnew)."""
    sql = """
        SELECT Corsia,
               note3 AS Descrizione,
               CASE WHEN note = 'Ordine3'   THEN 'Min --> Max'
                    WHEN note = 'OrdineMax'  THEN 'Max' END AS Tipo_Ordine,
               note1 AS Abilitata,
               note2 AS Lato,
               CASE WHEN matt_pom = 'M' THEN 'Mattino'
                    WHEN matt_pom = 'P' THEN 'Pome' END AS Matt_Pom,
               Lun, Mar, Mer, Gio, Ven, Sab, Dom
        FROM goldcursori.dbo.t_corsiaabilita1
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


def corsie_per_avvio() -> list[dict]:
    """Corsie da t_corsiaabilita (srviisnew) per il form di selezione."""
    sql = """
        SELECT TRIM(Corsia), TRIM(COALESCE(note3, '')), note1
        FROM goldcursori.dbo.t_corsiaabilita
        ORDER BY TRY_CAST(Corsia AS INT)
    """
    out: list[dict] = []
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql)
            for r in cur.fetchall():
                out.append({
                    'corsia':      str(r[0] or '').strip(),
                    'descrizione': str(r[1] or '').strip(),
                    'abilitata':   str(r[2] or '').strip().lower() == 'si',
                })
    except Exception:
        logger.exception("riordino_pdv.corsie_per_avvio: errore lettura t_corsiaabilita")
    return out


def avvia_job(corsie_selezionate: list[str]) -> tuple[bool, str | None]:
    """
    Aggiorna t_corsiaabilita in base alla selezione, poi avvia il SQL Agent
    job 'Riordino PDV' tramite sp_start_job (ritorna subito senza aspettare).
    Ritorna (ok, errore).
    """
    if not corsie_selezionate:
        return False, "Selezionare almeno una corsia."
    try:
        placeholders = ','.join(['%s'] * len(corsie_selezionate))
        with connections['goldreport'].cursor() as cur:
            cur.execute("UPDATE goldcursori.dbo.t_corsiaabilita SET note1='no'")
            cur.execute(
                f"UPDATE goldcursori.dbo.t_corsiaabilita"
                f" SET note1='si' WHERE TRIM(Corsia) IN ({placeholders})",
                corsie_selezionate,
            )
        # Blocco separato: l'UPDATE sopra è già committed prima di avviare il job
        with connections['goldreport'].cursor() as cur:
            cur.execute("EXEC msdb.dbo.sp_start_job @job_name=%s", [_JOB])
    except Exception as e:
        s = str(e)
        if '22022' in s or 'already running' in s.lower():
            return False, "Il riordino è già in corso — attendere il completamento."
        logger.exception("riordino_pdv.avvia_job: errore")
        return False, s
    return True, None


def stato_job() -> dict:
    """
    Controlla lo stato del job 'Riordino PDV'.
    Ritorna dict: running, succeeded, failed, messaggio.
    """
    try:
        with connections['goldreport'].cursor() as cur:
            # Controlla se il job è in esecuzione adesso (avviato nelle ultime 2 ore, non ancora finito)
            cur.execute("""
                SELECT COUNT(*) FROM msdb.dbo.sysjobactivity ja
                JOIN msdb.dbo.sysjobs j ON ja.job_id = j.job_id
                WHERE j.name = %s
                  AND ja.start_execution_date >= DATEADD(hour, -2, GETDATE())
                  AND ja.start_execution_date IS NOT NULL
                  AND ja.stop_execution_date IS NULL
            """, [_JOB])
            if cur.fetchone()[0] > 0:
                return {'running': True, 'succeeded': False, 'failed': False, 'messaggio': ''}

            # Controlla l'ultimo esito in sysjobhistory
            cur.execute("""
                SELECT TOP 1 jh.run_status, jh.message
                FROM msdb.dbo.sysjobhistory jh
                JOIN msdb.dbo.sysjobs j ON jh.job_id = j.job_id
                WHERE j.name = %s AND jh.step_id = 0
                ORDER BY jh.instance_id DESC
            """, [_JOB])
            row = cur.fetchone()
            if not row:
                # Job appena avviato, non ancora visibile in history
                return {'running': True, 'succeeded': False, 'failed': False, 'messaggio': ''}
            run_status, messaggio = row
            return {
                'running':   False,
                'succeeded': run_status == 1,
                'failed':    run_status in (0, 3),
                'messaggio': messaggio or '',
            }
    except Exception as e:
        logger.exception("riordino_pdv.stato_job: errore")
        return {'running': False, 'succeeded': False, 'failed': True, 'messaggio': str(e)}


def risultati_riordino() -> dict:
    """Conteggi e file generati dall'ultimo riordino."""
    out: dict = {'righe_ordine': 0, 'files': []}
    try:
        oggi = datetime.date.today().strftime('%d/%m/%Y')
        with connections['goldreport'].cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM goldcursori.dbo.t_OrdineGiorno")
            out['righe_ordine'] = cur.fetchone()[0] or 0
            cur.execute(
                "SELECT Corsia, NomeFile, note2, pOrigine"
                " FROM goldcursori.dbo.t_fileRio WHERE Data=%s ORDER BY Corsia",
                [oggi],
            )
            out['files'] = [
                {'corsia': r[0], 'nome': r[1], 'righe': r[2], 'path': r[3]}
                for r in cur.fetchall()
            ]
    except Exception:
        logger.exception("riordino_pdv.risultati_riordino: errore")
    return out
