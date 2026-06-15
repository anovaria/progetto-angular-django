import logging
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from . import services

logger = logging.getLogger(__name__)

_SESSION_CCOM = 'rio_fornitori_ccom'
_SESSION_DESCR = 'rio_fornitori_descr'


def home(request):
    ctx = {'errore': None}

    if request.method == 'POST':
        ccom = request.POST.get('ccom', '').strip()
        if not ccom.isdigit() or len(ccom) != 6:
            ctx['errore'] = "Inserire esattamente 6 cifre numeriche."
            ctx['ccom'] = ccom
            return render(request, 'rio_fornitori/home.html', ctx)

        fornitore = services.cerca_ccom(ccom)
        if not fornitore:
            ctx['errore'] = f"Codice {ccom} non trovato."
            ctx['ccom'] = ccom
            return render(request, 'rio_fornitori/home.html', ctx)

        request.session[_SESSION_CCOM] = fornitore['ccom']
        request.session[_SESSION_DESCR] = fornitore['descrccom']
        return redirect('rio_fornitori:ordine')

    return render(request, 'rio_fornitori/home.html', ctx)


def ordine(request):
    ccom = request.session.get(_SESSION_CCOM)
    descrccom = request.session.get(_SESSION_DESCR)

    if not ccom:
        return redirect('rio_fornitori:home')

    config = services.leggi_config_fornitore(ccom)

    ctx = {
        'ccom': ccom,
        'descrccom': descrccom,
        'config': config,
        'gg_cons_default': config['ggconsegna'] if config else 7,
        'gg_cop_default': config['ggcopertura'] if config else 35,
        'messaggio': None,
        'errore': None,
    }
    return render(request, 'rio_fornitori/ordine.html', ctx)


def modifica_email(request):
    ccom = request.session.get(_SESSION_CCOM)
    descrccom = request.session.get(_SESSION_DESCR)

    if not ccom:
        return redirect('rio_fornitori:home')

    config = services.leggi_config_fornitore(ccom)
    emails = config.get('emails_fornitore', []) if config else []

    ctx = {
        'ccom': ccom,
        'descrccom': descrccom,
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

    return render(request, 'rio_fornitori/modifica_email.html', ctx)


@require_POST
def esegui(request):
    ccom = request.session.get(_SESSION_CCOM)
    descrccom = request.session.get(_SESSION_DESCR)

    if not ccom:
        return redirect('rio_fornitori:home')

    try:
        gg_cons = int(request.POST.get('gg_cons', 7))
        gg_cop = int(request.POST.get('gg_cop', 35))
        tip_ord = int(request.POST.get('tip_ord', 0))
        riduzione = int(request.POST.get('riduzione_perc', 0))
        dove = request.POST.get('dove', 'Dash')
    except (ValueError, TypeError):
        config = services.leggi_config_fornitore(ccom)
        return render(request, 'rio_fornitori/ordine.html', {
            'ccom': ccom, 'descrccom': descrccom, 'config': config,
            'gg_cons_default': 7, 'gg_cop_default': 35,
            'errore': "Valori non validi. Controllare i campi.",
        })

    ok, errore = services.esegui_ordine(ccom, gg_cons, gg_cop, tip_ord, riduzione, dove, 1)

    if ok:
        try:
            send_mail(
                subject=f"Ordine lanciato da portale per CCOM {ccom}",
                message=f"Ordine lanciato da portale per CCOM {ccom} - {descrccom}.\n\nUtente: {(request.portal_user or {}).get('username', 'sconosciuto')}\nParametri: gg consegna={gg_cons}, gg copertura={gg_cop}, destinazione={dove}.",
                from_email=None,
                recipient_list=['alessandro.novaria@groscidac.it'],
                fail_silently=False,
            )
        except Exception:
            logger.exception("notifica email ordine: errore invio ccom=%s", ccom)

    config = services.leggi_config_fornitore(ccom)
    ctx = {
        'ccom': ccom,
        'descrccom': descrccom,
        'config': config,
        'gg_cons_default': gg_cons,
        'gg_cop_default': gg_cop,
        'messaggio': None if not ok else f"Proposta d'ordine creata su Dashboard Gold per {ccom} - {descrccom}.",
        'errore': errore if not ok else None,
    }
    return render(request, 'rio_fornitori/ordine.html', ctx)
