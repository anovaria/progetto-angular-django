from datetime import datetime
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from .models import PromoStorico, PromoTestata
from . import services

def promo_abbigliamento(request):
    codice_da_scaricare = request.session.get('codice_promo_creato', None)
    context = {
        'storico': PromoStorico.objects.all(),
        'prossimo_codice': services.prossimo_codice_promo(),
        'testate': PromoTestata.objects.all(),
        'codice_da_scaricare':codice_da_scaricare
    }

    return render(request, 'promo_abbigliamento/promo_abbigliamento.html', context)

def crea_testata(request):
    codice_promo = request.POST.get('codice_promo','').strip()
    descrizione = request.POST.get('descrizione','').strip()
    nome_file = request.POST.get('nome_file','').strip()
    data_inizio_sellout = request.POST.get('data_inizio_sellout','').strip()
    data_fine_sellout = request.POST.get('data_fine_sellout','').strip()
    if not services.descrizione_valida(descrizione):
        messages.error(request, 'La descrizione supera il limite di 50 caratteri')
        return redirect('promo_abbigliamento:home')
    if services.codice_gia_usato(codice_promo):
        messages.error(request, f'Il codice {codice_promo} è già presente ')
        return redirect('promo_abbigliamento:home')
    promo = PromoTestata.objects.create(
        codice_promo = codice_promo,
        descrizione = descrizione,
        data_inizio_sellout = datetime.strptime(data_inizio_sellout,'%Y-%m-%d').date(),
        data_fine_sellout = datetime.strptime(data_fine_sellout,'%Y-%m-%d').date(),
        tipo_promo='M',
        creato_da=request.portal_user['username']
    )
    request.session['codice_promo_creato'] = promo.codice_promo
    request.session['nome_file_creato'] = nome_file
    messages.success(request, f'Il codice {codice_promo} è stato creato con successo!')
    return redirect('promo_abbigliamento:home')

def scarica_csv_promo(request, codice_promo):
    promo = PromoTestata.objects.get(codice_promo=codice_promo)
    nome = request.session.pop('nome_file_creato', codice_promo)
    csv_bytes = services.genera_csv_promo(promo)
    response = HttpResponse(csv_bytes, content_type='text/csv; charset=cp1252')
    response['Content-Disposition'] = f'attachment; filename="{nome}.csv"'
    request.session.pop('codice_promo_creato', None)
    return response
