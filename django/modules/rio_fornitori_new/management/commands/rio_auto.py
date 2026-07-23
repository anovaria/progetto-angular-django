r"""
Management command: riordino fornitori AUTOMATICO.

Migra i 7 task legacy di srviis (Windows Task Scheduler -> sqlcmd ->
OrdineFornitore_04_dash @dove='Central' @mandaMail=1 -> trasffilerio.exe) nel
flusso Python del portale, come deciso con Carlo il 02/07/2026.

IMPORTANTE (corretto il 15/07/2026): il legacy usa il canale CENTRAL, non Dash.
Letto il sorgente completo di OrdineFornitore_04_dash: @dove='Central' scrive su
t_exportfoRio/t_fileRio e lancia trasffilerio.exe (lo STESSO exe di RIOQ10, non
trasffilerioDash.exe), che chiama la SP Oracle SIL_Rio. SIL_Rio fa Fase 1 e Fase
2 nella stessa chiamata (Stato=3 = ordine reale gia' scritto in CDEENTCDE): niente
tappa Dashboard annullabile lato Oracle, l'ordine e' gia' reale e si
valida/annulla direttamente in Gold - esattamente il comportamento storico da
riprodurre (vedi --canale sotto, default 'central').

Il calcolo della proposta (giacenze/rotazione/QTAMAX) resta IDENTICO e passa
sempre da OrdineFornitore_Dash (nessuna duplicazione della logica di calcolo,
gia' validata in produzione); cambia solo il secondo export verso Gold:

    services.esegui_ordine(ccom, ...)         # SP OrdineFornitore_Dash @skipExe=1
        -> services.costruisci_export_central() # ri-esporta in t_exportfoRio/t_fileRio
                                                 # (numfo/sito reali da Oracle, nuovo nr RFO)
        -> transfer.trasferisci_proposta_central() # CSV + SFTP + SIL_Rio (Python)

NON usa xp_cmdshell ne' l'exe legacy: il trasferimento a Gold e' in puro Python
(transfer.py, gia' validato in produzione dal riordino manuale per il canale Dash;
le funzioni *_central sono nuove, in dry-run per validazione).

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
from django.core.mail import EmailMessage
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
        parser.add_argument(
            '--canale',
            choices=['central', 'dash'],
            default='central',
            help="Canale di consegna a Gold. 'central' (default): riproduce il "
                 "comportamento storico dei 7 fornitori automatici legacy "
                 "(@dove='Central' del vecchio OrdineFornitore_04_dash) -> ordine "
                 "REALE creato subito in Gold (CDEENTCDE), validabile/annullabile "
                 "li', via la SP Oracle SIL_Rio. 'dash': usa lo stesso canale del "
                 "riordino manuale (Dashboard Gold, TST_*_DASH) - solo per confronto/test.",
        )
        parser.add_argument(
            '--salta-se-ordine-aperto',
            action='store_true',
            help="Guardia anti-doppione: prima di riordinare conta gli ordini gia' aperti "
                 "su Gold per il fornitore (cdeentcde ECDETAT=5, finestra -30/+10 gg) e, se "
                 "ce n'e' almeno uno, NON lancia il riordino (stato 'saltato'). Serve ai "
                 "fornitori schedulati ogni giorno (es. Onesti Group) per non accumulare "
                 "ordini doppi finche' il precedente non e' ricevuto.",
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
        canale = options.get('canale', 'central')
        salta_se_aperto = options.get('salta_se_ordine_aperto', False)
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
        self.stdout.write("Canale: %s" % canale)
        self.stdout.write('-' * 64)
        logger.info("rio_auto avviato: ccom=%s dry_run=%s canale=%s gg_cons=%s gg_cop=%s tip_ord=%s riduzione=%s",
                    ccoms, dry_run, canale, gg_cons_ovr, gg_cop_ovr, tip_ord, riduzione)

        # --- Elaborazione fornitore per fornitore -----------------------------
        # Un fallimento su un fornitore NON deve fermare gli altri: si raccoglie
        # l'esito di ciascuno e si prosegue.
        esiti = []  # lista di dict: {ccom, descr, stato, dettaglio}
        for ccom in ccoms:
            esiti.append(self._elabora_fornitore(
                ccom, tip_ord, riduzione, dry_run, gg_cons_ovr, gg_cop_ovr, salta_se_aperto, canale))

        # --- Riepilogo, notifica ed esito -------------------------------------
        ok = [e for e in esiti if e['stato'] == 'ok']
        vuoti = [e for e in esiti if e['stato'] == 'vuoto']
        saltati = [e for e in esiti if e['stato'] == 'saltato']
        falliti = [e for e in esiti if e['stato'] == 'errore']

        riepilogo = self._formatta_riepilogo(esiti, dry_run)
        self.stdout.write('-' * 64)
        self.stdout.write(riepilogo)
        self._invia_riepilogo(riepilogo, esiti, dry_run)

        # Codice di uscita: != 0 se ci sono stati fallimenti veri (SP/trasferimento).
        # I "vuoti" (nessun articolo da ordinare) NON sono un errore.
        if falliti:
            raise CommandError(
                "%d fornitore/i in errore: %s" % (len(falliti), ', '.join(e['ccom'] for e in falliti))
            )

    # ------------------------------------------------------------------ helper

    def _elabora_fornitore(self, ccom, tip_ord, riduzione, dry_run,
                           gg_cons_ovr=None, gg_cop_ovr=None, salta_se_aperto=False,
                           canale='central'):
        """
        Esegue il ciclo completo per un singolo fornitore e ritorna un dict di esito:
          stato = 'ok'      -> proposta creata e trasferita (o CSV generato in dry-run)
                = 'vuoto'   -> SP ok ma nessun articolo da ordinare
                = 'saltato' -> guardia attiva e ordine gia' aperto: riordino non lanciato
                = 'errore'  -> SP fallita, trasferimento a Gold fallito, o guardia non
                               verificabile (meglio non ordinare alla cieca -> segnalare)

        gg_cons_ovr / gg_cop_ovr: se valorizzati, sovrascrivono i giorni letti da
        t_masterfornrio (servono a replicare i valori hardcoded nei task legacy).
        salta_se_aperto: se True, applica la guardia anti-doppione prima della SP.
        canale: 'central' (default, comportamento storico dei 7 automatici legacy:
        ordine reale diretto in Gold via SIL_Rio) oppure 'dash' (Dashboard Gold,
        come il riordino manuale - solo per confronto/test).
        """
        descr = ''
        try:
            config = services.leggi_config_fornitore(ccom)
            if not config:
                self.stdout.write(self.style.ERROR("  [%s] fornitore non trovato in t_masterfornrio" % ccom))
                return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                        'dettaglio': 'Fornitore non presente in t_masterfornrio.'}

            descr = config.get('descrccom', '') or ''
            gg_cons = gg_cons_ovr if gg_cons_ovr is not None else config['ggconsegna']
            gg_cop = gg_cop_ovr if gg_cop_ovr is not None else config['ggcopertura']

            # 0) Guardia anti-doppione (solo se richiesta): se c'e' gia' un ordine aperto
            # su Gold per questo fornitore, NON si riordina. Se la conta non e'
            # verificabile, si segnala come errore (non si ordina alla cieca ne' si salta
            # in silenzio: un doppione/un salto muto sarebbero peggio di un rosso visibile).
            if salta_se_aperto:
                ok_g, n_aperti, err_g = services.conta_ordini_aperti(ccom)
                if not ok_g:
                    self.stdout.write(self.style.ERROR(
                        "  [%s] guardia ordini aperti non verificabile: %s" % (ccom, err_g)))
                    return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                            'dettaglio': 'Controllo ordini aperti fallito: %s' % err_g}
                if n_aperti > 0:
                    self.stdout.write(
                        "  [%s] %d ordine/i gia' aperto/i: riordino non lanciato" % (ccom, n_aperti))
                    return {'ccom': ccom, 'descr': descr, 'stato': 'saltato',
                            'dettaglio': '%d ordine/i gia\' aperto/i su Gold: riordino non lanciato.' % n_aperti}

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
            # Teniamo csv_bytes/rows: il CSV va allegato alla mail di riepilogo (chi
            # riceve vede la proposta completa senza accedere al server).
            if canale == 'central':
                # Canale storico dei 7 automatici legacy: la proposta e' gia'
                # calcolata (t_exportfoRiodash, passo 1 sopra); qui si ricostruisce
                # solo il SECONDO export verso le tabelle Central
                # (t_exportfoRio/t_fileRio) con numfo/sito reali da Oracle, un nuovo
                # numero RFO, e si invia via SIL_Rio (ordine reale diretto, niente
                # Dashboard). Vedi services.costruisci_export_central.
                ok_c, err_c, nr_ord_central, _n = services.costruisci_export_central(ccom, config.get('alg'))
                if not ok_c:
                    # Come sul canale Dash (msg_t == MSG_PROPOSTA_VUOTA piu' sotto):
                    # se al momento del secondo export la proposta e' vuota, non e'
                    # un errore ma "nessun articolo da ordinare" (es. tipOrd=1 sotto
                    # soglia, o legacy stesso giorno con "l'ordine non ha record").
                    if err_c == transfer.MSG_PROPOSTA_VUOTA:
                        self.stdout.write("  [%s] nessun articolo da ordinare" % ccom)
                        return {'ccom': ccom, 'descr': descr, 'stato': 'vuoto',
                                'dettaglio': 'Nessun articolo da ordinare.',
                                'nr_ord': nr_ord}
                    self.stdout.write(self.style.ERROR("  [%s] export Central fallito: %s" % (ccom, err_c)))
                    return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                            'dettaglio': 'Export canale Central fallito: %s' % err_c,
                            'nr_ord': nr_ord}
                nr_ord = nr_ord_central
                ok_t, msg_t, csv_bytes, rows = transfer.trasferisci_proposta_central(nr_ord, dry_run=dry_run)
            else:
                ok_t, msg_t, csv_bytes, rows = transfer.trasferisci_proposta(nr_ord, dry_run=dry_run)
            n_righe = len(rows) if rows else 0
            if ok_t:
                self.stdout.write(self.style.SUCCESS("  [%s] %s: %s" % (ccom, nr_ord, msg_t)))
                return {'ccom': ccom, 'descr': descr, 'stato': 'ok',
                        'dettaglio': '%s: %s' % (nr_ord, msg_t),
                        'nr_ord': nr_ord, 'csv': csv_bytes, 'n_righe': n_righe}
            # Proposta vuota rilevata dal transfer (la SP ha dato un nr_ord ma
            # t_exportfoRiodash e' vuota): NON e' un errore, e' "nessun articolo da
            # ordinare" -> stato 'vuoto' (mail informativa, exit 0), come i giorni in
            # cui la SP non genera nemmeno il nr_ord. Cosi' un tipOrd=1 sotto soglia
            # non tinge di rosso il task ne' manda una mail d'errore.
            if msg_t == transfer.MSG_PROPOSTA_VUOTA:
                self.stdout.write("  [%s] %s: nessun articolo da ordinare" % (ccom, nr_ord))
                return {'ccom': ccom, 'descr': descr, 'stato': 'vuoto',
                        'dettaglio': '%s: nessun articolo da ordinare.' % nr_ord,
                        'nr_ord': nr_ord}
            # SP ok ma trasferimento no: invio AMBIGUO, va segnalato come errore.
            # Alleghiamo comunque il CSV se generato: aiuta la diagnosi.
            self.stdout.write(self.style.ERROR("  [%s] %s trasferimento fallito: %s" % (ccom, nr_ord, msg_t)))
            return {'ccom': ccom, 'descr': descr, 'stato': 'errore',
                    'dettaglio': 'Proposta %s creata ma trasferimento a Gold fallito: %s' % (nr_ord, msg_t),
                    'nr_ord': nr_ord, 'csv': csv_bytes, 'n_righe': n_righe}

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
            simbolo = {'ok': 'OK   ', 'vuoto': 'VUOTO', 'saltato': 'SALT ', 'errore': 'ERR  '}[e['stato']]
            nome = (' %s' % e['descr']) if e.get('descr') else ''
            righe.append("  %s [%s]%s  %s" % (simbolo, e['ccom'], nome, e['dettaglio']))
        n_ok = sum(1 for e in esiti if e['stato'] == 'ok')
        n_vuoti = sum(1 for e in esiti if e['stato'] == 'vuoto')
        n_saltati = sum(1 for e in esiti if e['stato'] == 'saltato')
        n_err = sum(1 for e in esiti if e['stato'] == 'errore')
        testata = ("Riordino fornitori automatico - %s\n"
                   "Fornitori: %d  |  ok: %d  |  vuoti: %d  |  saltati: %d  |  errori: %d\n"
                   % (modo, len(esiti), n_ok, n_vuoti, n_saltati, n_err))
        return testata + '\n'.join(righe)

    def _invia_riepilogo(self, riepilogo, esiti, dry_run):
        """
        Invia SEMPRE la mail di riepilogo ai destinatari RIO_AUTO_MAIL_TO, con il CSV
        di ogni proposta ALLEGATO (chi riceve vede l'ordine completo senza accedere al
        server). Un errore d'invio email viene loggato ma non fa fallire il comando
        (gli ordini potrebbero essere gia' stati inviati a Gold).
        """
        destinatari = list(getattr(settings, 'RIO_AUTO_MAIL_TO', []) or [])
        if not destinatari:
            logger.warning("rio_auto: RIO_AUTO_MAIL_TO vuoto, nessuna mail di riepilogo inviata.")
            return

        ok = [e for e in esiti if e['stato'] == 'ok']
        falliti = [e for e in esiti if e['stato'] == 'errore']

        # Oggetto:
        #  - run a fornitore SINGOLO (caso piu' comune): stile legacy, riconoscibile
        #    ai destinatari -> "Ordine: <nrord> del fornitore : <ccom> - <descr> --> <esito>".
        #    "caricato in Gold" SOLO in reale a esito ok; in dry-run l'esito lo dice chiaro.
        #  - run MULTI fornitore (es. Perfetti 807764+807765): conteggio di riepilogo.
        if len(esiti) == 1:
            e = esiti[0]
            if e['stato'] == 'ok':
                esito = 'DRY RUN (non inviato)' if dry_run else 'caricato in Gold'
            elif e['stato'] == 'vuoto':
                esito = 'nessun articolo da ordinare'
            elif e['stato'] == 'saltato':
                esito = 'ordine gia\' aperto, riordino non lanciato'
            else:
                esito = 'ERRORE'
            subject = "Ordine: %s del fornitore : %s - %s --> %s" % (
                e.get('nr_ord') or '-', e['ccom'], e.get('descr') or '', esito)
        else:
            prefisso = '[DRY RUN] ' if dry_run else ''
            stato = 'ERRORI' if falliti else 'ok'
            subject = "%s[Riordino Fornitori Auto] %d ordini, %d errori (%s)" % (
                prefisso, len(ok), len(falliti), stato)
        try:
            email = EmailMessage(subject=subject, body=riepilogo, from_email=None, to=destinatari)
            # Allega il CSV di ogni fornitore che ne ha generato uno (proposte ok e
            # anche trasferimenti falliti, utili alla diagnosi). Nome file = <nrord>.csv.
            n_allegati = 0
            for e in esiti:
                csv_bytes = e.get('csv')
                if csv_bytes:
                    nomefile = "%s.csv" % (e.get('nr_ord') or e['ccom'])
                    email.attach(nomefile, csv_bytes, 'text/csv')
                    n_allegati += 1
            email.send(fail_silently=False)
            self.stdout.write("Mail di riepilogo inviata a: %s (%d allegati)" % (
                ', '.join(destinatari), n_allegati))
        except Exception:
            logger.exception("rio_auto: invio mail di riepilogo fallito")
            self.stdout.write(self.style.ERROR("Invio mail di riepilogo fallito (vedi log)."))
