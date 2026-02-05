"""
Views per app AssoArticoli
"""
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json

from .models import MasterAssortimenti, AllArticolo
from .barcode_utils import generate_ean13_svg, normalize_ean_for_barcode
from .excel_utils import export_articoli_excel, export_report_inventario


def index(request):
    """
    Maschera principale - Visualizzazione e filtro articoli per CCOM, Reparto, Sottoreparto, Famiglia, Linea
    """
    # Ottieni lista CCOM distinti per dropdown
    ccom_list = MasterAssortimenti.objects.using('goldreport').values(
        'ccom', 'descrccom'
    ).distinct().order_by('ccom')
    
    # Ottieni lista Reparti distinti
    rep_list = MasterAssortimenti.objects.using('goldreport').values(
        'rep', 'descrrep'
    ).distinct().order_by('rep')
    
    # Ottieni lista Sottoreparti distinti
    srep_list = MasterAssortimenti.objects.using('goldreport').values(
        'srep', 'descrsrep'
    ).distinct().order_by('srep')
    
    # Ottieni lista Famiglie distinte
    fam_list = MasterAssortimenti.objects.using('goldreport').values(
        'fam', 'descrfam'
    ).distinct().order_by('fam')
    
    # Filtri dalla request
    selected_ccom = request.GET.get('ccom', '')
    selected_rep = request.GET.get('rep', '')
    selected_srep = request.GET.get('srep', '')
    selected_fam = request.GET.get('fam', '')
    selected_linee = request.GET.getlist('linea')  # Selezione multipla
    linea_1_filter = request.GET.get('linea1', '') == '1'
    search_query = request.GET.get('search', '')
    
    # Lista linee per il CCOM selezionato (solo se L1 attivo e CCOM selezionato)
    linea_list = []
    if selected_ccom and linea_1_filter:
        linea_list = MasterAssortimenti.objects.using('goldreport').filter(
            ccom=selected_ccom,
            fornprinc=1
        ).values(
            'linea_prodotto', 'descr_linea'
        ).exclude(
            Q(linea_prodotto__isnull=True) | Q(linea_prodotto='')
        ).distinct().order_by('linea_prodotto')
    
    # Query base
    articoli_query = MasterAssortimenti.objects.using('goldreport').select_related()
    
    # Applica filtri
    if selected_ccom:
        articoli_query = articoli_query.filter(
            Q(ccom=selected_ccom) | Q(descrccom__icontains=selected_ccom)
        )
    
    if selected_rep:
        articoli_query = articoli_query.filter(rep=selected_rep)
    
    if selected_srep:
        articoli_query = articoli_query.filter(srep=selected_srep)
    
    if selected_fam:
        articoli_query = articoli_query.filter(fam=selected_fam)
    
    if linea_1_filter:
        # Filtra per fornitore principale
        articoli_query = articoli_query.filter(fornprinc=1)
        
        # Se selezionate linee specifiche, filtra per quelle
        if selected_linee:
            articoli_query = articoli_query.filter(linea_prodotto__in=selected_linee)
    
    if search_query:
        articoli_query = articoli_query.filter(
            Q(codart__icontains=search_query) |
            Q(descrart__icontains=search_query) |
            Q(ean__icontains=search_query)
        )
    
    # Ordina
    articoli_query = articoli_query.order_by('linea_prodotto', 'tipo_riordino', 'fam', 'codart')
    
    # Limita risultati per performance (paginazione manuale)
    page_size = 100
    articoli = articoli_query[:page_size]
    
    # Arricchisci con giacenze
    articoli_data = []
    for art in articoli:
        # Filtra per EANPRINC = 1 (EAN principale)
        giacenze = AllArticolo.objects.using('goldreport').filter(
            codart=art.codart,
            eanprinc=1
        ).first()
        
        if giacenze:
            giacenza_pdv = giacenze.giacenza_pdv or 0
            giacenza_dep = giacenze.giacenza_deposito or 0
        else:
            giacenza_pdv = 0
            giacenza_dep = 0
        
        # Genera barcode SVG
        ean_normalized = normalize_ean_for_barcode(art.ean, art.tipoean)
        barcode_svg = None
        if ean_normalized:
            barcode_svg = generate_ean13_svg(ean_normalized)
        
        articoli_data.append({
            'codart': art.codart,
            'descrart': art.descrart,
            'sett': art.sett,
            'rep': art.rep,
            'descrrep': art.descrrep,
            'srep': art.srep,
            'descrsrep': art.descrsrep,
            'fam': art.fam,
            'descrfam': art.descrfam,
            'ccom': art.ccom,
            'descrccom': art.descrccom,
            'linea_prodotto': art.linea_prodotto,
            'descr_linea': art.descr_linea,
            'tipo_riordino': art.tipo_riordino,
            'stato': art.stato,
            'ean': art.ean,
            'tipoean': art.tipoean,
            'giacenza_pdv': float(giacenza_pdv) if giacenza_pdv else 0,
            'giacenza_deposito': float(giacenza_dep) if giacenza_dep else 0,
            'pracq': float(art.pracq) if art.pracq else 0,
            'iva': float(art.iva) if art.iva else 0,
            'descforn': art.descforn,
            'barcode_svg': barcode_svg,
        })
    
    context = {
        'ccom_list': ccom_list,
        'rep_list': rep_list,
        'srep_list': srep_list,
        'fam_list': fam_list,
        'linea_list': linea_list,
        'articoli': articoli_data,
        'selected_ccom': selected_ccom,
        'selected_rep': selected_rep,
        'selected_srep': selected_srep,
        'selected_fam': selected_fam,
        'selected_linee': selected_linee,
        'linea1_checked': linea_1_filter,
        'search_query': search_query,
        'total_count': len(articoli_data),
    }
    
    return render(request, 'asso_articoli/main.html', context)


def api_linee_per_ccom(request):
    """
    API per ottenere lista Linee filtrate per CCOM (per dropdown a cascata)
    Chiamata via AJAX quando cambia CCOM e L1 è attivo
    """
    ccom = request.GET.get('ccom', '')
    
    if not ccom:
        return JsonResponse({'results': []})
    
    linee_query = MasterAssortimenti.objects.using('goldreport').filter(
        ccom=ccom,
        fornprinc=1  # Solo fornitore principale
    ).values(
        'linea_prodotto', 'descr_linea'
    ).exclude(
        Q(linea_prodotto__isnull=True) | Q(linea_prodotto='')
    ).distinct().order_by('linea_prodotto')
    
    linee_list = list(linee_query)
    
    return JsonResponse({'results': linee_list})


def export_excel_view(request):
    """
    Export Excel degli articoli con filtri applicati
    """
    # Ottieni stessi filtri della vista principale
    selected_ccom = request.GET.get('ccom', '')
    selected_rep = request.GET.get('rep', '')
    selected_srep = request.GET.get('srep', '')
    selected_fam = request.GET.get('fam', '')
    selected_linee = request.GET.getlist('linea')  # Selezione multipla
    linea_1_filter = request.GET.get('linea1', '') == '1'
    search_query = request.GET.get('search', '')
    
    # Query
    articoli_query = MasterAssortimenti.objects.using('goldreport').select_related()
    
    if selected_ccom:
        articoli_query = articoli_query.filter(
            Q(ccom=selected_ccom) | Q(descrccom__icontains=selected_ccom)
        )
    
    if selected_rep:
        articoli_query = articoli_query.filter(rep=selected_rep)
    
    if selected_srep:
        articoli_query = articoli_query.filter(srep=selected_srep)
    
    if selected_fam:
        articoli_query = articoli_query.filter(fam=selected_fam)
    
    if linea_1_filter:
        articoli_query = articoli_query.filter(fornprinc=1)
        if selected_linee:
            articoli_query = articoli_query.filter(linea_prodotto__in=selected_linee)
    
    if search_query:
        articoli_query = articoli_query.filter(
            Q(codart__icontains=search_query) |
            Q(descrart__icontains=search_query) |
            Q(ean__icontains=search_query)
        )
    
    articoli_query = articoli_query.order_by('linea_prodotto', 'tipo_riordino', 'fam', 'codart')
    
    # Prepara dati per export
    articoli_data = []
    for art in articoli_query[:500]:  # Limite per performance
        # Filtra per EANPRINC = 1 (EAN principale)
        giacenze = AllArticolo.objects.using('goldreport').filter(
            codart=art.codart,
            eanprinc=1
        ).first()
        
        if giacenze:
            giacenza_pdv = giacenze.giacenza_pdv or 0
            giacenza_dep = giacenze.giacenza_deposito or 0
        else:
            giacenza_pdv = 0
            giacenza_dep = 0
        
        articoli_data.append({
            'codart': art.codart,
            'descrart': art.descrart,
            'sett': art.sett,
            'rep': art.rep,
            'srep': art.srep,
            'fam': art.fam,
            'ccom': art.ccom,
            'linea_prodotto': art.linea_prodotto,
            'descr_linea': art.descr_linea,
            'stato': art.stato,
            'ean': art.ean,
            'tipoean': art.tipoean,
            'giacenza_pdv': float(giacenza_pdv) if giacenza_pdv else 0,
            'giacenza_deposito': float(giacenza_dep) if giacenza_dep else 0,
            'pracq': float(art.pracq) if art.pracq else 0,
            'iva': float(art.iva) if art.iva else 0,
            'descforn': art.descforn,
        })
    
    # Genera Excel
    excel_buffer = export_articoli_excel(articoli_data, filename='assortimenti', include_barcode=True)
    
    # Response
    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    filename = f'assortimenti_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def report_inventario(request):
    """
    Report inventario (equivalente a r_StampaInv)
    """
    ccom = request.GET.get('ccom', '')
    
    # Query articoli con giacenze
    articoli_query = MasterAssortimenti.objects.using('goldreport').filter(fornprinc=1)
    
    if ccom:
        articoli_query = articoli_query.filter(ccom=ccom)
    
    articoli_query = articoli_query.order_by('linea_prodotto', 'tipo_riordino', 'fam', 'codart')
    
    # Filtra solo articoli con giacenze > 0
    articoli_data = []
    for art in articoli_query[:300]:
        # Filtra per EANPRINC = 1 (EAN principale)
        giacenze = AllArticolo.objects.using('goldreport').filter(
            codart=art.codart,
            eanprinc=1
        ).first()
        
        if giacenze:
            giacenza_pdv = giacenze.giacenza_pdv or 0
            giacenza_dep = giacenze.giacenza_deposito or 0
            
            # Solo articoli con giacenze
            if giacenza_pdv > 0 or giacenza_dep > 0:
                articoli_data.append({
                    'codart': art.codart,
                    'descrart': art.descrart,
                    'ean': art.ean,
                    'tipoean': art.tipoean,
                    'ccom': art.ccom,
                    'descrccom': art.descrccom,
                    'linea_prodotto': art.linea_prodotto,
                    'giacenza_pdv': float(giacenza_pdv),
                    'giacenza_deposito': float(giacenza_dep),
                })
    
    # Se richiesto export
    if request.GET.get('export') == 'excel':
        excel_buffer = export_report_inventario(articoli_data, ccom=ccom)
        
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f'inventario_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    # Altrimenti render HTML
    context = {
        'articoli': articoli_data,
        'ccom': ccom,
    }
    
    return render(request, 'asso_articoli/report_inventario.html', context)


def report_reparto(request, tipo):
    """
    Report specifici per reparti (BAR, MACELLERIA)
    Equivalente a q_estrBar e q_estrMace
    
    Args:
        tipo: 'bar' o 'macelleria'
    """
    # Famiglie per reparto (dalla logica Access)
    FAMIGLIE = {
        'bar': ['8979', '8940', '8943', '8970', '8971', '8942', '8962'],
        'macelleria': ['8979', '8940', '8943', '8970', '8971', '8942', '8962'],
    }
    
    if tipo not in FAMIGLIE:
        return HttpResponse("Tipo reparto non valido", status=400)
    
    famiglie = FAMIGLIE[tipo]
    
    # Query
    articoli_query = MasterAssortimenti.objects.using('goldreport').filter(
        fam__in=famiglie,
        fornprinc=1
    ).order_by('fam', 'codart')
    
    # Prepara dati
    articoli_data = []
    for art in articoli_query:
        # Filtro per lunghezza EAN (logica Access: Len([ean]) > 3 per alcune FAM)
        if art.fam in ['8940', '8943', '8970']:
            if not art.ean or len(str(art.ean)) <= 3:
                continue
        
        # Filtra per EANPRINC = 1 (EAN principale)
        giacenze = AllArticolo.objects.using('goldreport').filter(
            codart=art.codart,
            eanprinc=1
        ).first()
        
        giacenza_pdv = giacenze.giacenza_pdv if giacenze else 0
        
        articoli_data.append({
            'sett': art.sett,
            'rep': art.rep,
            'descrrep': art.descrrep,
            'srep': art.srep,
            'fam': art.fam,
            'descrfam': art.descrfam,
            'codforn': art.codforn,
            'descforn': art.descforn,
            'ccom': art.ccom,
            'descrccom': art.descrccom,
            'codart': art.codart,
            'descrart': art.descrart,
            'stato': art.stato,
            'ean': art.ean,
            'tipoean': art.tipoean,
            'giacenza_pdv': float(giacenza_pdv) if giacenza_pdv else 0,
        })
    
    # Export Excel
    if request.GET.get('export') == 'excel':
        excel_buffer = export_articoli_excel(
            articoli_data, 
            filename=f'{tipo}_report',
            include_barcode=True
        )
        
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f'{tipo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    context = {
        'tipo': tipo.upper(),
        'articoli': articoli_data,
    }
    
    return render(request, 'asso_articoli/report_reparto.html', context)


def api_ccom_list(request):
    """
    API per ottenere lista CCOM (per autocomplete)
    """
    search = request.GET.get('q', '')
    
    ccom_query = MasterAssortimenti.objects.using('goldreport').values(
        'ccom', 'descrccom'
    ).distinct()
    
    if search:
        ccom_query = ccom_query.filter(
            Q(ccom__icontains=search) | Q(descrccom__icontains=search)
        )
    
    ccom_list = list(ccom_query.order_by('ccom')[:50])
    
    return JsonResponse({'results': ccom_list})
