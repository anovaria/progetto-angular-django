r"""
Management command: riordino fornitori AUTOMATICO.

Migra i 7 task legacy di srviis (Windows Task Scheduler -> sqlcmd ->
OrdineFornitore_04_dash @mandaMail=1 -> trasffilerioDash.exe) nel flusso Python
del portale, come deciso con Carlo il 02/07/2026.

Per ogni fornitore in --ccom esegue lo STESSO ciclo del riordino manuale, ma senza
interazione utente:

    services.esegui_ordine(ccom, ...)       # SP OrdineFornitore_Dash @skipExe=1
        -> transfer.trasferisci_proposta()   # CSV + SFTP + sil_rioDash + SSH (Python)

NON usa xp_cmdshell ne' l'exe legacy: il trasferimento a Gold e' in puro Python
(transfer.py, gia' validato in produzione dal riordino manuale).

Va schedulato da Windows Task Scheduler su Srv-Dev1 (dove gira il portale e il venv
con paramiko/oracledb), un task per cadenza. Esempi di riga di comando:

    <venv>\python.exe manage.py rio_auto --ccom 807764,807765     # Perfetti
    <venv>\python.exe manage.py rio_auto --ccom 806697            # Fornaio del Casale
    <venv>\python.exe manage.py rio_auto                          # lista RIO_AUTO_CCOM

DRY RUN
-------
Interruttore INDIPENDENTE dal riordino manuale (RIO_DASH_DRY_RUN):
    --dry-run       forza la simulazione (genera il CSV, niente invio a Gold);
    --no-dry-run    forza l'invio reale;
    (nessuno dei due) -> vale il setting RIO_AUTO_DRY_RUN (default: True = sicuro).

Cosi' si puo' pilotare l'automatico in dry-run mentre il manuale e' gia' in reale.

NOTIFICA ed ESITO
-----------------
Al termine invia SEMPRE una mail di riepilogo (successi + vuoti + fallimenti) ai
destinatari RIO_AUTO_MAIL_TO, cosi' un problema non passa inosservato (il legacy
notificava quasi tutto a 'silve@', casella probabilmente morta -> riordini "al buio").
Se almeno un fornitore FALLISCE, il comando esce con codice != 0: cosi' il task
risulta 'fallito' in Task Scheduler, a differenza del vecchio 0x1 silenzioso.
"""
import argparse
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from modules.rio_fornitori_new import services, transfer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Riordino fornitori automatico: lancia la proposta e il trasferimento a Gold per i CCOM indicati.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ccom',
            type=str,
            default='',
            help="Codici fornitore (CCOM) separati da virgola, es. 807764,807765. "
                 "Se omesso usa il setting RIO_AUTO_CCOM.",
        )
        parser.add_argument(
            '--gg-cons',
            type=int,
            default=None,
            help="Giorni consegna (@ggcons) da passare alla SP: determina la data di "
                 "consegna (getdate()+ggcons). Se omesso usa ggconsegna di t_masterfornrio. "
                 "NB: il task legacy di srviis hardcoda questo valore (es. Perfetti=3), "
                 "che puo' differire dalla tabella -> per fedelta' va passato esplicito.",
        )
        parser.add_argument(
            '--gg-cop',
            type=int,
            default=None,
            help="Giorni copertura (@ggcop) da passare alla SP. NB: per un fornitore "
                 "gia' presente la SP usa comunque ggcopertura di t_masterfornrio per le "
                 "quantita' (il param conta solo alla creazione del fornitore); si passa "
                 "per allinearsi allo script legacy. Se omesso usa ggcopertura della tabella.",
        )
        parser.add_argument(
            '--dry-run',
            action=argparse.BooleanOptionalAction,
            default=None,
            help="Forza (--dry-run) o disattiva (--no-dry-run) la simulazione. "
                 "Se non specificato vale il setting RIO_AUTO_DRY_RUN.",
        )
        parser.add_argument(
            '--tip-ord',
            type=int,
            default=0,
            help="Tipo ordine passato alla SP (@tipOrd). Default 0 (riordino standard).",
        )
        parser.add_argument(
            '--riduzione',
            type=int,
            default=0,
            help="Percentuale di riduzione (@perc = 100 - riduzione, solo se tip-ord=1). Default 0.",
        )

    def handle(self, *args, **options):
        # --- Risoluzione parametri --------------------------------------------
        ccom_arg = (options.get('ccom') or '').strip()
        if ccom_arg:
            ccoms = [c.strip() for c in ccom_arg.split(',') if c.strip()]
        else:
            ccoms = list(getattr(settings, 'RIO_AUTO_CCOM', []) or [])

        if not ccoms:
            raise CommandError(
                "Nessun fornitore da elaborare: passa --ccom 807764,... oppure imposta RIO_AUTO_CCOM."
            )

        # Dry-run esplicito da CLI (--dry-run/--no-dry-run) ha la precedenza sul setting.
        dry_run = options.get('dry_run')
        if dry_run is None:
            dry_run = getattr(settings, 'RIO_AUTO_DRY_RUN', True)

        tip_ord = options.get('tip_ord', 0)
        riduzione = options.get('riduzione', 0)
        # Override espliciti dei giorni (per replicare i valori hardcoded nei task
        # legacy di srviis). Se None si usano i valori di t_masterfornrio.
        gg_cons_ovr = options.get('gg_cons')
        gg_cop_ovr = options.get('gg_cop')

        self.stdout.write('=' * 64)
        self.stdout.write(self.style.WARNING('RIORDINO FORNITORI AUTOMATICO'))
        self.stdout.write('=' * 64)
        self.stdout.write("Fornitori: %s" % ', '.join(ccoms))
        self.stdout.write("Parametri: gg_cons=%s gg_cop=%s tip_ord=%s riduzione=%s" % (
            gg_cons_ovr if gg_cons_ovr is not None else 'da t_masterfornrio',
            gg_cop_ovr if gg_cop_ovr is not None else 'da t_masterfornrio',
            tip_ord, riduzione))
        self.stdout.write("Modalita': %s" % ('DRY RUN (nessun invio a Gold)' if dry_run else 'REALE (invio a Gold)'))
        self.stdout.write('-' * 64)
        logger.info("rio_auto avviato: ccom=%s dry_run=%s gg_cons=%s gg_cop=%s tip_ord=%s riduzione=%s",
                    ccoms, dry_run, gg_cons_ovr, gg_cop_ovr, tip_ord, riduzione)

        # --- Elaborazione fornitore per fornitore -----------------------------
        # Un fallimento su un fornitore NON deve fermare gli altri: si raccoglie
        # l'esito di ciascuno e si prosegue.
        esiti = []  # lista di dict: {ccom, descr, stato, dettaglio}
        for ccom in ccoms:
            esiti.append(self._elabora_fornitore(ccom, tip_ord, riduzione, dry_run, gg_cons_ovr, gg_cop_ovr))

        # --- Riepilogo, notifica ed esito -------------------------------------
        ok = [e for e in esiti if e['stato'] == 'ok']
        vuoti = [e for e in esiti if e['stato'] == 'vuoto']
        falliti = [e for e in esiti if e['stato'] == 'errore']

        riepilogo = self._formatta_riepilogo(esiti, dry_run)
        self.stdout.write('-' * 64)
        self.stdout.write(riepilogo)
        self._invia_riepilogo(riepilogo, ok, vuoti, falliti, dry_run)

        # Codice di uscita: != 0 se ci sono stati fallimenti veri (SP/trasferimento).
        # I "vuoti" (nessun articolo da ordinare) NON sono un errore.
        if falliti:
            raise CommandError(
                "%d fornitore/i in errore: %s" % (len(falliti), ', '.join(e['ccom'] for e in falliti))
            )

    # ------------------------------------------------------------------ helper

    def _elabora_fornitore(self, ccom, tip_ord, riduzione, dry_run, gg_cons_ovr=None, gg_cop_ovr=None):
        """
        Esegue il ciclo completo per un singolo fornitore e ritorna un dict di esito:
          stato = 'ok'     -> proposta creata e trasferita (o CSV generato in dry-run)
                = 'vuoto'  -> SP ok ma nessun articolo da ordinare
                = 'errore' -> SP fallita, oppure trasferimento a Gold fallito

        gg_cons_ovr / gg_cop_ovr: se valorizzati, sovrascrivono i giorni letti da
        t_masterfornrio (servono a replicare i valori hardcoded nei task legacy).
        """
        descr = ''
        try:
            config = services.leggi_config_fornitore(ccom)
            if not config:
                self.stdout.write(self.style.ERROR("  [%s] fornitore non trovato in t_masterfornrio" % ccom))
                return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                        'dettaglio': 'Fornitore non presente in t_masterfornrio.'}

            gg_cons = gg_cons_ovr if gg_cons_ovr is not None else config['ggconsegna']
            gg_cop = gg_cop_ovr if gg_cop_ovr is not None else config['ggcopertura']

            # 1) Calcolo proposta (SP OrdineFornitore_Dash @skipExe=1)
            ok, errore, nr_ord = services.esegui_ordine(ccom, gg_cons, gg_cop, tip_ord, riduzione)
            if not ok:
                self.stdout.write(self.style.ERROR("  [%s] SP fallita: %s" % (ccom, errore)))
                return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                        'dettaglio': 'SP OrdineFornitore_Dash fallita: %s' % errore}
            if not nr_ord:
                self.stdout.write("  [%s] nessun articolo da ordinare" % ccom)
                return {'ccom': ccom, 'descr': descr, 'stato': 'vuoto',
                        'dettaglio': 'Nessun articolo da ordinare.'}

            # 2) Trasferimento a Gold (o solo CSV in dry-run)
            ok_t, msg_t, _csv, _rows = transfer.trasferisci_proposta(nr_ord, dry_run=dry_run)
            if ok_t:
                self.stdout.write(self.style.SUCCESS("  [%s] %s: %s" % (ccom, nr_ord, msg_t)))
                return {'ccom': ccom, 'descr': descr, 'stato': 'ok',
                        'dettaglio': '%s: %s' % (nr_ord, msg_t)}
            # SP ok ma trasferimento no: invio AMBIGUO, va segnalato come errore.
            self.stdout.write(self.style.ERROR("  [%s] %s trasferimento fallito: %s" % (ccom, nr_ord, msg_t)))
            return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                    'dettaglio': 'Proposta %s creata ma trasferimento a Gold fallito: %s' % (nr_ord, msg_t)}

        except Exception as e:
            # Qualsiasi eccezione imprevista su un fornitore non deve fermare gli altri.
            logger.exception("rio_auto: errore imprevisto su ccom=%s", ccom)
            self.stdout.write(self.style.ERROR("  [%s] errore imprevisto: %s" % (ccom, e)))
            return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                    'dettaglio': 'Errore imprevisto: %s' % e}

    def _formatta_riepilogo(self, esiti, dry_run):
        """Costruisce il testo di riepilogo (usato sia a video sia nella mail)."""
        righe = []
        modo = 'DRY RUN (nessun invio a Gold)' if dry_run else 'REALE (invio a Gold)'
        for e in esiti:
            simbolo = {'ok': 'OK   ', 'vuoto': 'VUOTO', 'errore': 'ERR  '}[e['stato']]
            righe.append("  %s [%s] %s" % (simbolo, e['ccom'], e['dettaglio']))
        n_ok = sum(1 for e in esiti if e['stato'] == 'ok')
        n_vuoti = sum(1 for e in esiti if e['stato'] == 'vuoto')
        n_err = sum(1 for e in esiti if e['stato'] == 'errore')
        testata = ("Riordino fornitori automatico - %s\n"
                   "Fornitori: %d  |  ok: %d  |  vuoti: %d  |  errori: %d\n"
                   % (modo, len(esiti), n_ok, n_vuoti, n_err))
        return testata + '\n'.join(righe)

    def _invia_riepilogo(self, riepilogo, ok, vuoti, falliti, dry_run):
        """
        Invia SEMPRE la mail di riepilogo ai destinatari RIO_AUTO_MAIL_TO.
        Un errore d'invio email viene loggato ma non fa fallire il comando (gli
        ordini potrebbero essere gia' stati inviati a Gold).
        """
        destinatari = list(getattr(settings, 'RIO_AUTO_MAIL_TO', []) or [])
        if not destinatari:
            logger.warning("rio_auto: RIO_AUTO_MAIL_TO vuoto, nessuna mail di riepilogo inviata.")
            return

        prefisso = '[DRY RUN] ' if dry_run else ''
        stato = 'ERRORI' if falliti else 'ok'
        subject = "%s[Riordino Fornitori Auto] %d ordini, %d errori (%s)" % (
            prefisso, len(ok), len(falliti), stato)
        try:
            send_mail(
                subject=subject,
                message=riepilogo,
                from_email=None,
                recipient_list=destinatari,
                fail_silently=False,
            )
            self.stdout.write("Mail di riepilogo inviata a: %s" % ', '.join(destinatari))
        except Exception:
            logger.exception("rio_auto: invio mail di riepilogo fallito")
            self.stdout.write(self.style.ERROR("Invio mail di riepilogo fallito (vedi log)."))
