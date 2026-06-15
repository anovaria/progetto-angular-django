"""
views.py — Riordino PDV (Parametri Rio).

Pagina di amministrazione del portale che visualizza (SOLA LETTURA) la
schedulazione settimanale del riordino automatico PDV.
Le azioni dell'originale P_rio.aspx (Salva, Ripristina, riomanu, RIOQ10)
sono volutamente escluse in questa fase.
"""
import datetime

from django.shortcuts import render, redirect
from django.conf import settings

from . import services


def parametri_rio(request):
    # Funzione disattivata finché non è pronto il nuovo riordino (vedi RIO_PDV_ENABLED):
    # nasconde l'accesso anche a chi digita l'URL a mano.
    if not settings.RIO_PDV_ENABLED:
        return redirect('portal:home')

    giorni = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
    oggi = giorni[datetime.date.today().weekday()]
    return render(request, 'riordino_pdv/parametri_rio.html', {
        'righe':  services.schedule(),
        'giorni': giorni,
        'oggi':   oggi,
    })
