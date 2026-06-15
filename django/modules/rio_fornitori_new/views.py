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
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from . import services
from . import transfer

logger = logging.getLogger(__name__)

# Chiavi di sessione (prefissate con il nome app per non collidere con la
# vecchia app rio_fornitori che gira in parallelo).
_SESSION_CCOM = 'rio_fornitori_new_ccom'
_SESSION_DESCR = 'rio_fornitori_new_descr'


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
    messaggio = None
    if ok and nr_ord:
        # La SP ha popolato t_exportfoRiodash: ora il portale genera il CSV e
        # (se non in dry-run) fa SFTP + sil_rioDash + SSH verso Gold, al posto
        # del vecchio trasffileriodash.exe.
        ok_trasf, msg_trasf = transfer.trasferisci_proposta(nr_ord)
        if ok_trasf:
            messaggio = f"Proposta {nr_ord} ({ccom} - {descrccom}): {msg_trasf}"
        else:
            # SP riuscita ma trasferimento no: lo segnaliamo come errore.
            ok = False
            errore = f"Proposta {nr_ord} creata, ma trasferimento a Gold fallito: {msg_trasf}"
    elif ok and not nr_ord:
        # SP riuscita ma nessun numero ordine = nessun articolo da ordinare.
        ok = False
        errore = "Nessun articolo da ordinare per questo fornitore."

    # --- 4. Notifica via email (solo se tutto e' andato a buon fine) ---
    if ok:
        try:
            send_mail(
                subject=f"[TEST srviisnew] Ordine lanciato da portale per CCOM {ccom}",
                message=f"Ordine lanciato da portale per CCOM {ccom} - {descrccom}.\n\nUtente: {(request.portal_user or {}).get('username', 'sconosciuto')}\nParametri: gg consegna={gg_cons}, gg copertura={gg_cop}.",
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
    }
    return render(request, 'rio_fornitori_new/ordine.html', ctx)
