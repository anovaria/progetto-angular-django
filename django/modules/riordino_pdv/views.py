"""views.py — Riordino PDV (Parametri Rio)."""
import datetime

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from . import services, transfer


def parametri_rio(request):
    if not settings.RIO_PDV_ENABLED:
        return redirect('portal:home')

    giorni = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
    oggi = giorni[datetime.date.today().weekday()]
    return render(request, 'riordino_pdv/parametri_rio.html', {
        'righe':        services.schedule(),
        'corsie_avvio': services.corsie_per_avvio(),
        'giorni':       giorni,
        'oggi':         oggi,
    })


@require_POST
def avvia_htmx(request):
    if not settings.RIO_PDV_ENABLED:
        return HttpResponseBadRequest()

    corsie_sel = request.POST.getlist('corsie')
    ok, errore = services.avvia_job(corsie_sel)
    return render(request, 'riordino_pdv/_stato_job.html', {
        'errore': errore,
        'avviato': ok,
    })


def stato_htmx(request):
    if not settings.RIO_PDV_ENABLED:
        return HttpResponseBadRequest()

    stato = services.stato_job()
    ctx = {'stato': stato}

    if stato['succeeded']:
        ctx['risultati'] = services.risultati_riordino()
        try:
            ok_tr, msg_tr = transfer.trasferisci_ordini()
            ctx['trasferimento'] = {'ok': ok_tr, 'msg': msg_tr}
        except Exception as e:
            ctx['trasferimento'] = {'ok': False, 'msg': str(e)}

    return render(request, 'riordino_pdv/_stato_job.html', ctx)
