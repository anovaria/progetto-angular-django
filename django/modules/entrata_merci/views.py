from datetime import datetime
import io
from django.shortcuts import render
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from .models import V_RicevimentiGoldArtFo,EntrataMerciOverride
from django.db.models import F
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from .services import calcola_ean13, get_righe_magazzino, get_righe_pdv

def report_pdf_magazzino(request):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        righe = get_righe_magazzino(request)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()
        elementi = []
        elementi.append(Paragraph("Entrata Merci - Magazzino", styles['Title']))
        elementi.append(Spacer(1, 12))
        dati_tabella = [['Data Ric', 'Reparto', 'CCom', 'CodArtFo', 'Cod Articolo', 
                        'EAN', 'Descrizione', 'Stato', 'UM', 'Qta Ric', 'Pz X UIMB', 'Giac PDV']]
        righe_da_evidenziare = []  # indici delle righe con giacenza < 5
        for indice, riga in enumerate(righe, start=1):  # start=1 perché la riga 0 è l'intestazione
            if riga['giacenza_pdv'] is not None and riga['giacenza_pdv'] < 5:
                righe_da_evidenziare.append(indice)
            dati_tabella.append([
                riga['data_ricevimento'].strftime('%d/%m/%Y'),
                riga['reparto'],
                riga['contr_comm'],
                riga['codartfo'],
                riga['cod_art'],
                riga['ean_13'],
                riga['desc_art'][:35] + '...' if riga['desc_art'] and len(riga['desc_art']) > 35 else riga['desc_art'],
                riga['stato'],
                riga['unita_misura'],
                str(int(riga['quantita_ricevuta'])) if riga['quantita_ricevuta'] is not None else '',
                str(int(riga['pzxcart'])) if riga['pzxcart'] is not None else '',
                str(int(riga['giacenza_pdv'])) if riga['giacenza_pdv'] is not None else '',
            ])
        tabella = Table(dati_tabella, colWidths=[
            50,   # Data Ric
            150,  # Reparto
            40,   # CCom
            45,   # CodArtFo
            50,   # Cod Articolo
            65,   # EAN
            200,  # Descrizione
            20,   # Stato
            35,   # UM
            45,   # Qta Ric
            20,   # Pz X UIMB
            45,   # Giac PDV
        ])
        stile_base = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]

        for indice in righe_da_evidenziare:
            stile_base.append(('BACKGROUND', (0, indice), (-1, indice), colors.pink))

        tabella.setStyle(TableStyle(stile_base))
        elementi.append(tabella)
        elementi.append(Spacer(1, 24))
        data_generazione = datetime.now().strftime('%d/%m/%Y %H:%M')
        utente = request.portal_user.get('username')
        elementi.append(Paragraph(f"Generato il {data_generazione} da {utente}", styles['Normal']))
        doc.build(elementi)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')

def report_pdf_pdv(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    righe = get_righe_pdv(request)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    elementi = []
    elementi.append(Paragraph("Entrata Merci - PDV", styles['Title']))
    elementi.append(Spacer(1, 12))
    dati_tabella = [['Data Ric', 'Settore', 'Reparto', 'CCom', 'CodArtFo', 'Cod Articolo', 
                    'EAN', 'Descrizione', 'Stato', 'UM', 'Qta Ric', 'Co', 'Ca', 'Giac PDV']]
    righe_da_evidenziare = []  # indici delle righe con giacenza < 5
    for indice, riga in enumerate(righe, start=1):  # start=1 perché la riga 0 è l'intestazione
        if riga['giacenza_pdv'] is not None and riga['giacenza_pdv'] < 5:
            righe_da_evidenziare.append(indice)
        dati_tabella.append([
            riga['data_ricevimento'].strftime('%d/%m/%Y'),
            riga['settore'],
            riga['reparto'],
            riga['contr_comm'],
            riga['codartfo'],
            riga['cod_art'],
            riga['ean_13'],
            riga['desc_art'][:35] + '...' if riga['desc_art'] and len(riga['desc_art']) > 35 else riga['desc_art'],
            riga['stato'],
            riga['unita_misura'],
            str(int(riga['quantita_ricevuta'])) if riga['quantita_ricevuta'] is not None else '',
            str(int(riga['corsia'])) if riga['corsia'] is not None else '',
            str(int(riga['campata'])) if riga['campata'] is not None else '',
            str(int(riga['giacenza_pdv'])) if riga['giacenza_pdv'] is not None else '',
        ])
    tabella = Table(dati_tabella, colWidths=[
        50,   # Data Ric
        55,   # Settore
        150,   # Reparto
        40,   # CCom
        45,   # CodArtFo
        50,   # Cod Articolo
        65,   # EAN
        200,  # Descrizione
        20,   # Stato
        35,   # UM
        45,   # Qta Ric
        20,   # Corsia
        20,   # Campata
        45,   # Giac PDV
    ])

    stile_base = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]

    for indice in righe_da_evidenziare:
        stile_base.append(('BACKGROUND', (0, indice), (-1, indice), colors.pink))

    tabella.setStyle(TableStyle(stile_base))
    elementi.append(tabella)
    elementi.append(Spacer(1, 24))
    data_generazione = datetime.now().strftime('%d/%m/%Y %H:%M')
    utente = request.portal_user.get('username')
    elementi.append(Paragraph(f"Generato il {data_generazione} da {utente}", styles['Normal']))
    doc.build(elementi)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

def entrata_merci_magazzino(request):
    righe_finali = get_righe_magazzino(request)
    paginator = Paginator(righe_finali, 30)  # 30 righe per pagina, es.
    numero_pagina = request.GET.get('pagina')
    pagina_corrente = paginator.get_page(numero_pagina)  
    return render(request, 'entrata_merci/entrata_merci_magazzino.html', {
        'merciMagazzino': pagina_corrente,
        'conteggio':len(righe_finali)
    })
            
def entrata_merci_pdv(request):
    righe_finali = get_righe_pdv(request)
    paginator = Paginator(righe_finali, 30)  # 30 righe per pagina, es.
    numero_pagina = request.GET.get('pagina')
    pagina_corrente = paginator.get_page(numero_pagina)  
    return render(request, 'entrata_merci/entrata_merci_pdv.html', {
        'merciPdv': pagina_corrente,
        'conteggio':len(righe_finali)
    })

def modifica_data(request, pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    cod_art = request.POST.get('cod_art')
    valore = request.POST.get('valore')
    utente = request.portal_user.get('username')
    try:
        data_finale = datetime.strptime(valore, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'errore': 'Data non valida'}, status=400)
    EntrataMerciOverride.objects.update_or_create(
        cod_interno_ric= pk,
        cod_art = cod_art,
        defaults={
            'data_ricevimento_modificata': data_finale,
            'utente': utente,
        }
    )
    return JsonResponse({'ok': True})

def tronca(testo, lunghezza=35):
    if testo is None:
        return ''
    testo = str(testo)
    if len(testo) > lunghezza:
        return testo[:lunghezza] + '...'
    return testo