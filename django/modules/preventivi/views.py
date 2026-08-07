from django.shortcuts import render
from .models import VMasterData
from openpyxl import Workbook
from django.http import HttpResponse

def preventivi(request):
    if request.method == 'POST':
        if('verifica' in request.POST):
            risultati, testo_originale, non_trovati = cerca_articoli(request)
            return render(request, 'preventivi/preventivi.html', {'risultati': risultati, 'testo_originale': testo_originale, 'non_trovati': non_trovati})
        elif 'esporta' in request.POST:
            risultati, testo_originale, non_trovati  = cerca_articoli(request)
            wb = Workbook()
            ws = wb.active
            ws.append(['Contratto Comm.', 'Descrizione Ccom', 'Codice EAN', 'Cod. art. forn.', 'Codice Articolo', 'Descrizione Articolo', 'Prezzo Vend. cadauno'])
            for articolo in risultati:
                ws.append([articolo.CCOM, articolo.DESCRCCOM, articolo.EAN, articolo.CODARTFO, articolo.CODART, articolo.DESCRART, articolo.PRZ_VEND])
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="preventivo.xlsx"'
            wb.save(response)
            return response
        else:
            return render(request, 'preventivi/preventivi.html', {})
    else:
         return render(request, 'preventivi/preventivi.html', {})

def cerca_articoli(request):
    raw_input = request.POST.get("codici_articolo", "")
    righe = raw_input.split('\n')
    codici = [r.strip() for r in righe if r.strip()]
    codici_unici = set(codici)
    risultati = []
    non_trovati = []
    for codice in codici_unici:
        articolo = VMasterData.objects.filter(CODART=codice).first()
        if articolo:
            risultati.append(articolo)
        else:
            non_trovati.append(codice)
    return risultati, raw_input, non_trovati