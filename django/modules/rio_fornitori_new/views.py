"""
views.py - Viste dell'app rio_fornitori_new (riordino fornitori su srviisnew).

Flusso utente:
  home          -> inserimento del codice fornitore (6 cifre)
  ordine        -> parametri della proposta e pulsante di lancio
  esegui        -> lancia la SP e il trasferimento a Gold (POST)
  modifica_email-> gestione delle email di notifica del fornitore

Il codice fornitore selezionato viene tenuto in sessione tra una pagina e l'altra.
"""
import logging
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from . import services
from . import transfer

logger = logging.getLogger(__name__)

# Chiavi di sessione (prefissate con il nome app per non collidere con la
# vecchia app rio_fornitori che gira in parallelo).
_SESSION_CCOM = 'rio_fornitori_new_ccom'
_SESSION_DESCR = 'rio_fornitori_new_descr'
# Numero dell'ultima proposta generata: serve alla vista di download del CSV.
_SESSION_CSV_NR = 'rio_fornitori_new_csv_nr'

# Indici delle colonne utili per l'anteprima, dentro le righe di transfer.EXPORT_COLUMNS.
_COL_CODART = 5
_COL_VL = 6
_COL_DATACONS = 9
_COL_QTA = 10


def home(request):
    """Pagina iniziale: l'utente inserisce il codice fornitore (6 cifre numeriche)."""
    ctx = {'errore': None}

    if request.method == 'POST':
        ccom = request.POST.get('ccom', '').strip()
        # Validazione: esattamente 6 cifre.
        if not ccom.isdigit() or len(ccom) != 6:
            ctx['errore'] = "Inserire esattamente 6 cifre numeriche."
            ctx['ccom'] = ccom
            return render(request, 'rio_fornitori_new/home.html', ctx)

        # Verifica che il fornitore esista davvero.
        fornitore = services.cerca_ccom(ccom)
        if not fornitore:
            ctx['errore'] = f"Codice {ccom} non trovato."
            ctx['ccom'] = ccom
            return render(request, 'rio_fornitori_new/home.html', ctx)

        # Salva il fornitore in sessione e passa alla schermata ordine.
        request.session[_SESSION_CCOM] = fornitore['ccom']
        request.session[_SESSION_DESCR] = fornitore['descrccom']
        return redirect('rio_fornitori_new:ordine')

    return render(request, 'rio_fornitori_new/home.html', ctx)


def ordine(request):
    """Schermata della proposta: mostra i parametri del fornitore e il form di lancio."""
    ccom = request.session.get(_SESSION_CCOM)
    descrccom = request.session.get(_SESSION_DESCR)

    # Se non c'e' un fornitore in sessione, torna alla home.
    if not ccom:
        return redirect('rio_fornitori_new:home')

    config = services.leggi_config_fornitore(ccom)

    ctx = {
        'ccom': ccom,
        'descrccom': descrccom,
        'config': config,
        # Default precompilati nel form (7 / 35 se il fornitore non ha valori).
        'gg_cons_default': config['ggconsegna'] if config else 7,
        'gg_cop_default': config['ggcopertura'] if config else 35,
        'messaggio': None,
        'errore': None,
    }
    return render(request, 'rio_fornitori_new/ordine.html', ctx)


def modifica_email(request):
    """Gestione delle 4 email di notifica del fornitore (lettura e salvataggio)."""
    ccom = request.session.get(_SESSION_CCOM)
    descrccom = request.session.get(_SESSION_DESCR)

    if not ccom:
        return redirect('rio_fornitori_new:home')

    config = services.leggi_config_fornitore(ccom)
    emails = config.get('emails_fornitore', []) if config else []

    ctx = {
        'ccom': ccom,
        'descrccom': descrccom,
        # Precompila i 4 campi con le email esistenti (vuoto se mancano).
        'email0': emails[0] if len(emails) > 0 else '',
        'email1': emails[1] if len(emails) > 1 else '',
        'email2': emails[2] if len(emails) > 2 else '',
        'email3': emails[3] if len(emails) > 3 else '',
        'messaggio': None,
        'errore': None,
    }

    if request.method == 'POST':
        e0 = request.POST.get('email0', '').strip()
        e1 = request.POST.get('email1', '').strip()
        e2 = request.POST.get('email2', '').strip()
        e3 = request.POST.get('email3', '').strip()
        ok, errore = services.aggiorna_email_fornitore(ccom, e0, e1, e2, e3)
        ctx.update({'email0': e0, 'email1': e1, 'email2': e2, 'email3': e3})
        if ok:
            ctx['messaggio'] = "Email aggiornate."
        else:
            ctx['errore'] = errore

    return render(request, 'rio_fornitori_new/modifica_email.html', ctx)


@require_POST
def esegui(request):
    """
    Lancia la proposta d'ordine (solo POST).

    Passi:
      1. legge e valida i parametri dal form;
      2. chiama services.esegui_ordine() che esegue la SP (con @skipExe=1) e
         restituisce il numero ordine;
      3. chiama transfer.trasferisci_proposta() che genera il CSV e lo invia a Gold
         (in dry-run si ferma al CSV);
      4. se tutto ok invia una email di notifica e mostra l'esito.
    """
    ccom = request.session.get(_SESSION_CCOM)
    descrccom = request.session.get(_SESSION_DESCR)

    if not ccom:
        return redirect('rio_fornitori_new:home')

    # --- 1. Lettura e validazione parametri del form ---
    try:
        gg_cons = int(request.POST.get('gg_cons', 7))
        gg_cop = int(request.POST.get('gg_cop', 35))
        tip_ord = int(request.POST.get('tip_ord', 0))
        riduzione = int(request.POST.get('riduzione_perc', 0))
    except (ValueError, TypeError):
        config = services.leggi_config_fornitore(ccom)
        return render(request, 'rio_fornitori_new/ordine.html', {
            'ccom': ccom, 'descrccom': descrccom, 'config': config,
            'gg_cons_default': 7, 'gg_cop_default': 35,
            'errore': "Valori non validi. Controllare i campi.",
        })

    # --- 2. Esecuzione della SP (calcolo proposta + popolamento tabelle) ---
    ok, errore, nr_ord = services.esegui_ordine(ccom, gg_cons, gg_cop, tip_ord, riduzione)

    # --- 3. Trasferimento a Gold (CSV/SFTP/Oracle/SSH, o solo CSV in dry-run) ---
    # I messaggi indicano sempre all'utente SE l'ordine e' arrivato a Gold e se puo'
    # rilanciare in sicurezza, cosi' da evitare ordini duplicati su Gold:
    #   - successo            -> proposta inviata, NON ripetere;
    #   - errore prima del nr -> niente e' arrivato alla Dashboard, si puo' riprovare;
    #   - trasferimento fallito dopo la creazione -> invio AMBIGUO, non rilanciare.
    messaggio = None
    proposta_righe = None   # righe da mostrare in anteprima nella schermata di esito
    csv_scaricabile = False
    if ok and nr_ord:
        # La SP ha popolato t_exportfoRiodash: ora il portale genera il CSV e
        # (se non in dry-run) fa SFTP + sil_rioDash + SSH verso Gold, al posto
        # del vecchio trasffileriodash.exe.
        ok_trasf, msg_trasf, csv_bytes, csv_rows = transfer.trasferisci_proposta(nr_ord)
        # Se il CSV e' stato generato (anche se il trasferimento e' poi fallito),
        # prepara l'anteprima e rende disponibile il download del file.
        if csv_rows:
            proposta_righe = [{
                'codart': r[_COL_CODART], 'vl': r[_COL_VL],
                'data': r[_COL_DATACONS], 'qta': r[_COL_QTA],
            } for r in csv_rows]
            request.session[_SESSION_CSV_NR] = nr_ord
            csv_scaricabile = True
        if ok_trasf:
            messaggio = f"Proposta {nr_ord} ({ccom} - {descrccom}): {msg_trasf}"
        else:
            # SP riuscita ma trasferimento no: l'invio a Gold potrebbe essere
            # avvenuto solo in parte (es. file gia' caricato), quindi NON va
            # rilanciato alla cieca.
            ok = False
            errore = (f"Proposta {nr_ord} creata, ma il trasferimento alla Dashboard non e' andato "
                      f"a buon fine: {msg_trasf} Non rilanciare la proposta: contatta ITD per "
                      f"verificare se e' comunque arrivata alla Dashboard.")
    elif ok and not nr_ord:
        # SP riuscita ma nessun numero ordine = nessun articolo da ordinare.
        ok = False
        errore = "Nessun articolo da ordinare per questo fornitore. Nessuna proposta inviata alla Dashboard."
    elif not ok:
        # La SP non e' arrivata a creare la proposta (es. fornitore non trovato,
        # conflitto sulle tabelle di lavoro, DB occupato): alla Dashboard non e'
        # andato nulla, quindi il rilancio e' sicuro.
        errore = f"{errore} Nessuna proposta e' stata inviata alla Dashboard: puoi riprovare."

    # --- 4. Notifica via email (solo se tutto e' andato a buon fine) ---
    if ok:
        try:
            send_mail(
                subject=f"[Riordino Fornitori] Ordine {nr_ord} lanciato da portale per CCOM {ccom}",
                message=f"Ordine {nr_ord} lanciato da portale per CCOM {ccom} - {descrccom}.\n\nUtente: {(request.portal_user or {}).get('username', 'sconosciuto')}\nParametri: gg consegna={gg_cons}, gg copertura={gg_cop}.",
                from_email=None,
                recipient_list=['alessandro.novaria@groscidac.it'],
                fail_silently=False,
            )
        except Exception:
            # L'invio email non deve far fallire l'operazione: si logga e basta.
            logger.exception("notifica email ordine: errore invio ccom=%s", ccom)

    # Ricarica la schermata ordine con l'esito (messaggio di successo o errore).
    config = services.leggi_config_fornitore(ccom)
    ctx = {
        'ccom': ccom,
        'descrccom': descrccom,
        'config': config,
        'gg_cons_default': gg_cons,
        'gg_cop_default': gg_cop,
        'messaggio': messaggio,
        'errore': errore if not ok else None,
        'proposta_righe': proposta_righe,
        'csv_scaricabile': csv_scaricabile,
    }
    return render(request, 'rio_fornitori_new/ordine.html', ctx)


def scarica_csv(request):
    """
    Scarica il CSV dell'ultima proposta generata in questa sessione (lo stesso file
    inviato/da inviare alla Dashboard). Il numero ordine e' preso dalla sessione, non
    dall'utente, cosi' non c'e' rischio di path traversal.
    """
    nr_ord = request.session.get(_SESSION_CSV_NR)
    if not nr_ord:
        return redirect('rio_fornitori_new:home')

    data = transfer.leggi_csv_salvato(nr_ord)
    if data is None:
        return HttpResponse("File non piu' disponibile.", status=404)

    response = HttpResponse(data, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % nr_ord
    return response
