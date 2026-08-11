import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import ScansioneOrtofrutta,Ean
from .services import estrai_barcode, risolvi_articolo
from decimal import Decimal

def scansione(request):
    oggi= datetime.date.today()
    scansioni_oggi = ScansioneOrtofrutta.objects.filter(creato_il__date=oggi).order_by('-creato_il')
    for riga in scansioni_oggi:
        articolo = Ean.objects.filter(CODART=riga.codart).first()
        riga.descrart = articolo.DESCRART if articolo else ''
    return render(request, 'ortofrutta/scansione.html', {'scansioni_oggi' : scansioni_oggi})

def scansione_modifica_pesoqta(request,pk):
    if request.method == 'POST':
        riga = get_object_or_404(ScansioneOrtofrutta, pk=pk)
        valore = request.POST.get('valore')
        articolo  = Ean.objects.filter(CODART=riga.codart).first()
        descrart = articolo.DESCRART if articolo else ''
        if riga.gest == 'Kilogrammi':
            riga.peso_num = Decimal(valore)
        else:
            riga.qta = Decimal(valore)
        riga.save()
        return JsonResponse({
            'ok': True,
            'id': riga.id,
            'ean': riga.ean_scansionato,
            'codart': riga.codart,
            'descrart': descrart,
            'gest': riga.gest,
            'utente': riga.utente,
            'peso_num': str(riga.peso_num) if riga.peso_num is not None else '',
            'qta': str(riga.qta) if riga.qta is not None else '',
            'trovato': bool(articolo),
            'data_competenza': riga.data_competenza.strftime('%d/%m/%Y') if riga.data_competenza else '',
        })

def scansione_modifica_data(request, pk):
    if request.method == 'POST':
        riga = get_object_or_404(ScansioneOrtofrutta, pk=pk)
        valore = request.POST.get('valore')
        riga.data_competenza = datetime.datetime.strptime(valore, '%Y-%m-%d').date()
        riga.save()
        return JsonResponse({
            'ok' : True,
            'data_competenza': riga.data_competenza.strftime('%d/%m/%Y')
            })

def scansione_elimina(request,pk):
    if request.method == 'POST':
        riga = get_object_or_404(ScansioneOrtofrutta, pk=pk)
        riga.delete()
        return JsonResponse({'ok' : True})

def scansione_salva(request):
    if request.method == 'POST':
        raw = request.POST.get('codice', '')
        ean13 = estrai_barcode(raw)
        if ean13 is None:
            return JsonResponse({'ok': False, 'errore': 'Codice non riconosciuto'}, status=400)
        info = risolvi_articolo(ean13)
        qta = Decimal('1') if info['gest'] != 'Kilogrammi' else None
        riga = ScansioneOrtofrutta.objects.create(
            ean_scansionato = ean13,
            data_competenza = None,
            codart = info['codart'],
            peso_num = info['peso_num'],
            qta = qta,
            gest = info['gest'],
            utente = request.portal_user.get('username'),
        )
        return JsonResponse({
            'ok': True,
            'id': riga.id,
            'ean': riga.ean_scansionato,
            'codart': riga.codart,
            'descrart': info['descrart'],
            'gest': riga.gest,
            'utente': riga.utente,
            'peso_num': str(riga.peso_num) if riga.peso_num is not None else '',
            'qta': str(riga.qta) if riga.qta is not None else '',
            'trovato': bool(info['codart']),
            'data_competenza': riga.data_competenza.strftime('%Y-%m-%d') if riga.data_competenza else '',
        })
