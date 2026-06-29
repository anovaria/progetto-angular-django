"""
transfer.py — Trasferimento file CSV ordini PDV a Gold in puro Python.
Sostituisce TrasfFileRio.exe.

Differenze rispetto a rio_fornitori_new/transfer.py:
- I CSV sono già su disco (generati da EstraRio_new via BCP): nessuna
  generazione in Python.
- Ci sono N file per run (uno per corsia/lato): si cicla su t_fileRio
  WHERE elab='0'.
- SP Oracle: SIL_RIO invece di sil_rioDash.
- SSH viene eseguito UNA VOLTA sola dopo aver trasferito tutti i file.
- t_fileRio: elab '0'→pending, '2'→ok, '-1'→errore; EsitoImport 'Ok'/'No'.

MODALITA' DRY RUN
-----------------
Se RIO_PDV_DRY_RUN è attivo (default), logga i file trovati ma NON esegue
SFTP/Oracle/SSH e NON modifica t_fileRio.
"""
import io
import logging
import os

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)


class TransferError(Exception):
    pass


def _cfg(name, default=None):
    return getattr(settings, name, default)


def _pending_files():
    """
    Legge da t_fileRio i file in attesa di trasferimento (elab='0').
    Ritorna lista di dict con NomeFile, pOrigine, pDestinaz.
    """
    sql = "SELECT NomeFile, pOrigine, pDestinaz FROM goldcursori.dbo.t_fileRio WHERE elab = '0'"
    with connections['goldreport'].cursor() as cur:
        cur.execute(sql)
        return [
            {'NomeFile': r[0].strip(), 'pOrigine': r[1].strip(), 'pDestinaz': r[2].strip()}
            for r in cur.fetchall()
        ]


def _sftp_upload(local_path, remote_dir, filename):
    import paramiko

    host     = _cfg('RIO_PDV_SFTP_HOST', '172.17.10.41')
    port     = int(_cfg('RIO_PDV_SFTP_PORT', 22))
    user     = _cfg('RIO_PDV_SFTP_USER', 'glpcenadm')
    password = _cfg('RIO_PDV_SFTP_PASS', '')

    if not password:
        raise TransferError("RIO_PDV_SFTP_PASS non configurata.")

    remote_path = remote_dir.rstrip('/') + '/' + filename

    transport = paramiko.Transport((host, port))
    try:
        transport.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(local_path, remote_path)
        logger.info("SFTP ok: %s -> %s", filename, remote_path)
    finally:
        transport.close()


def _oracle_sil_rio(nomefile):
    """
    Chiama SIL_RIO su Oracle GOLDPROD.
    Firma assunta: SIL_RIO(NomeFile IN VARCHAR2, Stato OUT NUMBER, P_F_ERR OUT VARCHAR2).
    Ritorna (stato, messaggio). Stato 0/1 = errore inequivocabile; 2 = ok.
    """
    import oracledb

    dsn      = _cfg('RIO_PDV_ORACLE_DSN',  'Srvoracle.groscidac.local:1521/GOLDPROD')
    user     = _cfg('RIO_PDV_ORACLE_USER', 'GOLDCEN')
    password = _cfg('RIO_PDV_ORACLE_PASS', '')
    proc     = _cfg('RIO_PDV_ORACLE_PROC', 'SIL_RIO')

    if not password:
        raise TransferError("RIO_PDV_ORACLE_PASS non configurata.")

    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    try:
        cur = conn.cursor()
        stato = cur.var(oracledb.NUMBER)
        ferr  = cur.var(oracledb.STRING)
        cur.callproc(proc, [nomefile, stato, ferr])
        conn.commit()
        sv = stato.getvalue()
        return (int(sv) if sv is not None else None), (ferr.getvalue() or '')
    finally:
        conn.close()


def _ssh_run():
    import paramiko

    host     = _cfg('RIO_PDV_SFTP_HOST', '172.17.10.41')
    port     = int(_cfg('RIO_PDV_SFTP_PORT', 22))
    user     = _cfg('RIO_PDV_SFTP_USER', 'glpcenadm')
    password = _cfg('RIO_PDV_SFTP_PASS', '')
    cmd      = _cfg('RIO_PDV_SSH_CMD', '/gold/glp/central/shell/./gc_xls_xlsord.sh')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port=port, username=user, password=password, timeout=30)
        _, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        if err.strip():
            logger.warning("SSH stderr (%s): %s", cmd, err.strip())
        logger.info("SSH ok: %s", cmd)
        return out
    finally:
        ssh.close()


def _update_file(nomefile, elab, esito):
    sql = "UPDATE goldcursori.dbo.t_fileRio SET elab=%s, EsitoImport=%s WHERE NomeFile=%s"
    with connections['goldreport'].cursor() as cur:
        cur.execute(sql, [elab, esito, nomefile])


def _safe_update(nomefile, elab, esito):
    try:
        _update_file(nomefile, elab, esito)
    except Exception:
        logger.exception("Impossibile aggiornare t_fileRio per %s", nomefile)


def trasferisci_ordini():
    """
    Trasferisce tutti i file PDV in attesa (elab='0') a Gold.

    Per ogni file: SFTP → SIL_RIO → aggiorna t_fileRio.
    Al termine (se almeno un file ok): SSH gc_xls_xlsord.sh.

    Ritorna (ok, messaggio) dove ok=True se almeno un file è andato a buon fine.
    """
    try:
        files = _pending_files()
    except Exception as e:
        logger.exception("trasferisci_ordini: errore lettura t_fileRio")
        return False, "Errore lettura t_fileRio: %s" % e

    if not files:
        return False, "Nessun file da trasferire (t_fileRio elab='0' vuota)."

    if _cfg('RIO_PDV_DRY_RUN', True):
        logger.info("DRY RUN: %d file trovati in t_fileRio: %s",
                    len(files), [f['NomeFile'] for f in files])
        return True, ("DRY RUN: %d file trovati, nessun invio a Gold (SFTP/Oracle/SSH saltati)."
                      % len(files))

    ok_count = 0
    errors = []

    for f in files:
        nome    = f['NomeFile']
        origine = f['pOrigine']
        dest    = f['pDestinaz']
        local   = os.path.join(origine, nome)

        # SFTP
        try:
            _sftp_upload(local, dest, nome)
        except Exception as e:
            logger.exception("trasferisci_ordini: SFTP fallito per %s", nome)
            _safe_update(nome, '-1', 'No')
            errors.append("%s: SFTP fallito (%s)" % (nome, e))
            continue

        # Oracle SIL_RIO
        try:
            stato, msg = _oracle_sil_rio(nome)
            logger.info("SIL_RIO %s: Stato=%s, msg=%s", nome, stato, msg)
            if stato in (0, 1):
                logger.error("SIL_RIO: import fallito %s (Stato=%s): %s", nome, stato, msg)
                _safe_update(nome, '-1', 'No')
                errors.append("%s: SIL_RIO fallito (Stato=%s)" % (nome, stato))
                continue
        except Exception as e:
            logger.exception("trasferisci_ordini: SIL_RIO fallito per %s", nome)
            _safe_update(nome, '-1', 'No')
            errors.append("%s: Oracle fallito (%s)" % (nome, e))
            continue

        _safe_update(nome, '2', 'Ok')
        ok_count += 1

    # SSH una sola volta al termine, solo se almeno un file è stato trasferito
    if ok_count > 0:
        try:
            _ssh_run()
        except Exception as e:
            logger.exception("trasferisci_ordini: SSH fallito")
            errors.append("SSH fallito: %s" % e)

    if errors:
        msg = "%d/%d file ok. Errori: %s" % (ok_count, len(files), '; '.join(errors))
        return ok_count > 0, msg

    return True, "%d file trasferiti a Gold." % ok_count
