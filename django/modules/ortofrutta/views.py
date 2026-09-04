import io
import datetime
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse,HttpResponseNotAllowed
from .models import ScansioneOrtofrutta,Ean,ListinoGiorno
from .services import estrai_barcode, risolvi_articolo, totali_con_prezzo
from decimal import Decimal,InvalidOperation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def report_pdf(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    totali = totali_con_prezzo()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    elementi = []
    elementi.append(Paragraph("Report Cassa - Ortofrutta", styles['Title']))
    elementi.append(Spacer(1, 12))

    dati_tabella = [['Cod. Articolo', 'Descrizione', 'Gest', 'Quantità', 'Prezzo Unitario', 'Totale']]
    for riga in totali:
        dati_tabella.append([
            riga['codart'],
            riga['descrart'],
            riga['gest'],
            f"{riga['quantita']:.3f}" if riga['quantita'] is not None else '',   # sotto "Quantità" -> quantita
            riga['prezzo_listino'],
            f"{riga['valore']:.2f}" if riga['valore'] is not None else '',       # sotto "Totale" -> valore
        ])

    tabella = Table(dati_tabella)
    tabella.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elementi.append(tabella)
    elementi.append(Spacer(1, 24))
    data_generazione = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    utente = request.portal_user.get('username')
    elementi.append(Paragraph(f"Generato il {data_generazione} da {utente}", styles['Normal']))
    doc.build(elementi)
    buffer.seek(0)
    condizione = Q()
    for riga in totali:
        condizione |= Q(codart=riga['codart'], data_competenza=riga['data_competenza'])
    if totali:
        ScansioneOrtofrutta.objects.filter(condizione, fatturato=False).update(fatturato=True)
    nome_file = f"report_cassa_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nome_file}"'
    return response

def report(request):
    totali = totali_con_prezzo()
    return render(request, 'ortofrutta/report.html', {'totali': totali})

def listino_salva(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    codart = request.POST.get('codart')
    data_str = request.POST.get('data')
    prezzo = request.POST.get('prezzo')

    try:
        data_competenza = datetime.datetime.strptime(data_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'errore': 'Data non valida'}, status=400)

    if not prezzo:
        ListinoGiorno.objects.filter(codart=codart, data_competenza=data_competenza).delete()
        return JsonResponse({'ok': True})

    try:
        prezzo_decimal = Decimal(prezzo)
    except InvalidOperation:
        return JsonResponse({'ok': False, 'errore': 'Prezzo non valido'}, status=400)

    ListinoGiorno.objects.update_or_create(
        codart=codart,
        data_competenza=data_competenza,
        defaults={
            'prezzo_listino': prezzo_decimal,
            'utente_inserimento': request.portal_user.get('username'),
        },
    )
    return JsonResponse({'ok': True})

def listino(request):
    totali = totali_con_prezzo(solo_con_prezzo=False)
    return render(request, 'ortofrutta/listino.html', {'totali': totali})

def scansione(request):
    oggi= datetime.date.today()
    scansioni_oggi = ScansioneOrtofrutta.objects.filter(creato_il__date=oggi).order_by('-creato_il')
    for riga in scansioni_oggi:
        articolo = Ean.objects.filter(CODART=riga.codart).first()
        riga.descrart = articolo.DESCRART if articolo else ''
    return render(request, 'ortofrutta/scansione.html', {'scansioni_oggi' : scansioni_oggi})

def scansione_modifica_pesoqta(request, pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    riga = get_object_or_404(ScansioneOrtofrutta, pk=pk)
    valore = request.POST.get('valore')
    articolo = Ean.objects.filter(CODART=riga.codart).first()
    descrart = articolo.DESCRART if articolo else ''

    if not valore:
        valore_decimal = None
    else:
        try:
            valore_decimal = Decimal(valore)
        except InvalidOperation:
            return JsonResponse({'ok': False, 'errore': 'Valore non valido'}, status=400)

    if riga.gest == 'Kilogrammi':
        riga.peso_num = valore_decimal
    else:
        riga.qta = valore_decimal

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
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    riga = get_object_or_404(ScansioneOrtofrutta, pk=pk)
    valore = request.POST.get('valore')

    if not valore:
        riga.data_competenza = None
    else:
        try:
            riga.data_competenza = datetime.datetime.strptime(valore, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'errore': 'Data non valida'}, status=400)

    riga.save()

    return JsonResponse({
        'ok': True,
        'data_competenza': riga.data_competenza.strftime('%d/%m/%Y') if riga.data_competenza else '',
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
        ultima = ScansioneOrtofrutta.objects.filter(
            utente=request.portal_user.get('username'),
            data_competenza__isnull=False,
        ).order_by('-creato_il').first()
        data_precedente = ultima.data_competenza if ultima else None
        riga = ScansioneOrtofrutta.objects.create(
            ean_scansionato = ean13,
            data_competenza = data_precedente,
            codart = info['codart'],
            peso_num = info['peso_num'],
            qta = qta,
            gest = info['gest'],
            utente = request.portal_user.get('username')
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
