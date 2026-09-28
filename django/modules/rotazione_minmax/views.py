from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.gzip import gzip_page
from django.views.decorators.http import require_GET

from . import services


@require_GET
def index(request):
    ctx = {'siti': services.elenco_siti()}
    return render(request, 'rotazione_minmax/index.html', ctx)

@require_GET
@gzip_page
def dati(request):
    try:
        sito = int(request.GET.get('sito', ''))
    except ValueError:
        return JsonResponse({'errore': 'Parametro sito mancante o non valido'}, status=400)
    righe = services.righe_rotazione(sito)
    return JsonResponse({'righe': righe, 'totale': len(righe)})