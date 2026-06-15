"""
Modulo views per l'app AssoArticoli.

Gestisce la visualizzazione e il filtro degli articoli dell'assortimento
letti dalla vista MasterAssortimenti del database GoldReport.
Supporta filtri per CCOM, Reparto, Sottoreparto, Famiglia, Linea Prodotto,
ricerca per codice articolo o EAN, e vari report di export Excel.

Le giacenze (PDV e Deposito) vengono lette in join dalla tabella AllArticolo.
"""
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.db import connections
from datetime import datetime
import json

from .models import MasterAssortimenti, AllArticolo
from .barcode_utils import generate_ean13_svg, normalize_ean_for_barcode
from .excel_utils import export_articoli_excel, export_report_inventario



def _espandi_ean_list(ean_list):
    """Per EAN a 12 cifre aggiunge la variante con zero iniziale (EAN-13); viceversa per 13 cifre con zero."""
    result = []
    for e in ean_list:
        result.append(e)
        if e.isdigit():
            if len(e) == 12:
                result.append('0' + e)
            elif len(e) == 13 and e.startswith('0'):
                result.append(e[1:])
    return result


def _bulk_giacenze(codart_iter):
    """Carica giacenze per tutti i codart con una sola query. Restituisce {codart: AllArticolo}."""
    codarts = list({c for c in codart_iter if c})
    if not codarts:
        return {}
    return {g.codart: g for g in AllArticolo.objects.using('goldreport').filter(codart__in=codarts, eanprinc=1)}


def _filtra_per_codici(articoli_query, codart_list, ean_list):
    """Filtra per lista codici articolo e/o EAN (cerca anche in AllArticolo per EAN alternativi)."""
    if not codart_list and not ean_list:
        return articoli_query
    q = Q()
    if codart_list:
        q |= Q(codart__in=codart_list)
    if ean_list:
        ean_espanso = _espandi_ean_list(ean_list)
        # Match esatto su MasterAssortimenti (ean e eana)
        q_ean = Q(ean__in=ean_espanso) | Q(eana__in=ean_espanso)
        # Cerca anche in AllArticolo per EAN alternativi non presenti in MasterAssortimenti
        codarts_da_ean = list(
            AllArticolo.objects.using('goldreport').filter(ean__in=ean_espanso)
            .values_list('codart', flat=True).distinct()
        )
        if codarts_da_ean:
            q_ean |= Q(codart__in=codarts_da_ean)
        q |= q_ean
    return articoli_query.filter(q)


def _query_masterdataall(selected_ccom='', selected_rep='', selected_srep='', selected_fam='',
                          selected_descr='', codart_list=None, ean_list=None):
    """Query su t_masterdataall che include articoli con stato E e V, escludendo gli A (Annullati).
    Usata quando l'utente vuole vedere anche articoli in esaurimento/venduto.
    """
    codart_list = codart_list or []
    ean_list = ean_list or []

    query = """
    SELECT DISTINCT
        m.CODART, m.DESCRART, m.STATO,
        m.REP, m.DESCRREP, m.SREP, m.DESCRSREP,
        m.FAM, m.DESCRFAM, m.CCOM, m.DESCRCCOM,
        m.CODFORN, m.DESCFORN, m.EAN, m.PRACQ, m.IVA
    FROM dbo.t_masterdataall m
    WHERE m.STATO != 'A'
    """
    params = []

    if selected_ccom:
        query += " AND m.CCOM = %s"
        params.append(selected_ccom)
    if selected_rep:
        query += " AND m.REP = %s"
        params.append(selected_rep)
    if selected_srep:
        query += " AND m.SREP = %s"
        params.append(selected_srep)
    if selected_fam:
        query += " AND m.FAM = %s"
        params.append(selected_fam)
    if selected_descr:
        query += " AND m.DESCRART LIKE %s"
        params.append(f"%{selected_descr}%")
    if codart_list:
        placeholders = ','.join(['%s'] * len(codart_list))
        query += f" AND m.CODART IN ({placeholders})"
        params.extend(codart_list)
    if ean_list:
        ean_espanso = _espandi_ean_list(ean_list)
        placeholders = ','.join(['%s'] * len(ean_espanso))
        query += f" AND m.EAN IN ({placeholders})"
        params.extend(ean_espanso)

    query += " ORDER BY m.REP, m.DESCRART"

    with connections['goldreport'].cursor() as cursor:
        cursor.execute(query, params)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _build_articolo_da_masterdata(row, giacenze=None):
    """Costruisce il dizionario articolo dal risultato raw di t_masterdataall."""
    codart = row.get('CODART') or ''
    ean = row.get('EAN') or ''
    ean_normalized = normalize_ean_for_barcode(ean, None)
    barcode_svg = generate_ean13_svg(ean_normalized) if ean_normalized else None
    return {
        'codart': codart,
        'descrart': row.get('DESCRART') or '',
        'sett': '',
        'rep': row.get('REP') or '',
        'descrrep': row.get('DESCRREP') or '',
        'srep': row.get('SREP') or '',
        'descrsrep': row.get('DESCRSREP') or '',
        'fam': row.get('FAM') or '',
        'descrfam': row.get('DESCRFAM') or '',
        'ccom': row.get('CCOM') or '',
        'descrccom': row.get('DESCRCCOM') or '',
        'linea_prodotto': '',
        'descr_linea': '',
        'tipo_riordino': '',
        'stato': row.get('STATO') or '',
        'ean': ean,
        'tipoean': None,
        'giacenza_pdv': float(giacenze.giacenza_pdv or 0) if giacenze else 0,
        'giacenza_deposito': float(giacenze.giacenza_deposito or 0) if giacenze else 0,
        'pracq': float(row.get('PRACQ') or 0),
        'iva': float(row.get('IVA') or 0),
        'descforn': row.get('DESCFORN') or '',
        'barcode_svg': barcode_svg,
        'codartfo': '',
    }


def index(request):
    """
    Maschera principale - Visualizzazione e filtro articoli per CCOM, Reparto,
    Sottoreparto, Famiglia, Linea. Limita i risultati a 100 per performance.

    Logica di visualizzazione:
    - Se non è attivo alcun filtro, non carica i dati (ha_filtri = False).
    - Per ogni articolo recupera la giacenza PDV e deposito da AllArticolo
      filtrando per eanprinc=1 (solo EAN principale).
    - Genera il barcode SVG tramite la libreria barcode_utils.
    - Deduplicazione per codart tramite set seen_codart.
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

    # Filtri dalla request GET
    selected_ccom = request.GET.get('ccom', '')
    selected_rep = request.GET.get('rep', '')
    selected_srep = request.GET.get('srep', '')
    selected_fam = request.GET.get('fam', '')
    selected_linee = request.GET.getlist('linea')  # Selezione multipla
    linea_1_filter = request.GET.get('linea1', '') == '1'
    selected_descr = request.GET.get('descr', '')
    selected_stato = request.GET.get('stato', '')
    codart_list_raw = request.GET.get('codart_list', '')
    ean_list_raw = request.GET.get('ean_list', '')
    # Converti le stringhe separate da virgola in liste
    codart_list = [c.strip() for c in codart_list_raw.split(',') if c.strip()] if codart_list_raw else []
    ean_list = [e.strip() for e in ean_list_raw.split(',') if e.strip()] if ean_list_raw else []

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

    # Query base senza filtri
    articoli_query = MasterAssortimenti.objects.using('goldreport').select_related()

    # Applica filtri progressivamente
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
        # Filtra per fornitore principale (fornprinc=1)
        articoli_query = articoli_query.filter(fornprinc=1)

        # Se selezionate linee specifiche, filtra per quelle
        if selected_linee:
            articoli_query = articoli_query.filter(linea_prodotto__in=selected_linee)

    articoli_query = _filtra_per_codici(articoli_query, codart_list, ean_list)
    if selected_descr:
        articoli_query = articoli_query.filter(descrart__icontains=selected_descr)
    if selected_stato:
        articoli_query = articoli_query.filter(stato=selected_stato)

    articoli_query = articoli_query.order_by('linea_prodotto', 'tipo_riordino', 'fam', 'codart')

    # Verifica se è attivo almeno un filtro per decidere se caricare i dati
    has_filters = any([selected_ccom, selected_rep, selected_srep, selected_fam, selected_linee, linea_1_filter, codart_list, ean_list])

    if not has_filters:
        # Nessun filtro attivo: non mostrare dati (risparmio di query costose)
        articoli_data = []
    elif selected_stato == 'con_ea':
        # Include E e V (esclusi A): usa t_masterdataall, più completa di v_MasterAssortimenti
        raw_rows = _query_masterdataall(
            selected_ccom, selected_rep, selected_srep, selected_fam,
            selected_descr, codart_list, ean_list,
        )
        giacenze_map = _bulk_giacenze(row['CODART'] for row in raw_rows)
        articoli_data = []
        seen_codart = set()
        for row in raw_rows:
            if row['CODART'] in seen_codart:
                continue
            seen_codart.add(row['CODART'])
            articoli_data.append(_build_articolo_da_masterdata(row, giacenze_map.get(row['CODART'])))
    else:
        articoli_data = []
        seen_codart = set()  # Deduplicazione: un articolo può apparire più volte per linee diverse
        articoli_list = list(articoli_query)
        giacenze_map = _bulk_giacenze(art.codart for art in articoli_list)
        for art in articoli_list:
            if art.codart in seen_codart:
                continue
            seen_codart.add(art.codart)
            giacenze = giacenze_map.get(art.codart)

            if giacenze:
                giacenza_pdv = giacenze.giacenza_pdv or 0
                giacenza_dep = giacenze.giacenza_deposito or 0
            else:
                giacenza_pdv = 0
                giacenza_dep = 0

            # Genera barcode SVG per la visualizzazione nel browser
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
                'codartfo': art.codartfo,
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
        'total_count': len(articoli_data),
        'selected_descr': selected_descr,
        'selected_stato': selected_stato,
        'has_filters': has_filters,
        'codart_list_raw': codart_list_raw,
        'ean_list_raw': ean_list_raw,
        'codart_list_count': len(codart_list),
        'ean_list_count': len(ean_list),
    }

    return render(request, 'asso_articoli/main.html', context)


def api_linee_per_ccom(request):
    """
    API per ottenere la lista delle Linee Prodotto filtrate per CCOM.
    Usata via AJAX per il dropdown a cascata: quando l'utente seleziona
    un CCOM e attiva il filtro Fornitore Principale, il JS carica le linee
    disponibili per quel CCOM con questa chiamata.
    Restituisce JSON con lista di {linea_prodotto, descr_linea}.
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
    Export Excel completo degli articoli con gli stessi filtri applicati
    nella pagina principale. Limite: 500 articoli per performance.
    Include barcode EAN13 nel file tramite la libreria excel_utils.
    Il nome del file include timestamp per evitare conflitti.
    """
    selected_ccom = request.GET.get('ccom', '')
    selected_rep = request.GET.get('rep', '')
    selected_srep = request.GET.get('srep', '')
    selected_fam = request.GET.get('fam', '')
    selected_linee = request.GET.getlist('linea')
    linea_1_filter = request.GET.get('linea1', '') == '1'
    selected_descr = request.GET.get('descr', '')
    selected_stato = request.GET.get('stato', '')
    codart_list_raw = request.GET.get('codart_list', '')
    ean_list_raw = request.GET.get('ean_list', '')
    codart_list = [c.strip() for c in codart_list_raw.split(',') if c.strip()] if codart_list_raw else []
    ean_list = [e.strip() for e in ean_list_raw.split(',') if e.strip()] if ean_list_raw else []

    # Costruisce la query con gli stessi filtri della vista index
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

    articoli_query = _filtra_per_codici(articoli_query, codart_list, ean_list)
    if selected_descr:
        articoli_query = articoli_query.filter(descrart__icontains=selected_descr)
    if selected_stato:
        articoli_query = articoli_query.filter(stato=selected_stato)

    articoli_query = articoli_query.order_by('linea_prodotto', 'tipo_riordino', 'fam', 'codart')

    # Prepara dati per export (limite 500 per performance)
    articoli_data = []
    seen_codart = set()

    if selected_stato == 'con_ea':
        raw_rows = _query_masterdataall(
            selected_ccom, selected_rep, selected_srep, selected_fam,
            selected_descr, codart_list, ean_list,
        )
        giacenze_map = _bulk_giacenze(row['CODART'] for row in raw_rows)
        for row in raw_rows:
            if row['CODART'] in seen_codart:
                continue
            seen_codart.add(row['CODART'])
            d = _build_articolo_da_masterdata(row, giacenze_map.get(row['CODART']))
            articoli_data.append({
                'codart': d['codart'], 'descrart': d['descrart'],
                'sett': d['sett'], 'rep': d['rep'], 'srep': d['srep'],
                'fam': d['fam'], 'ccom': d['ccom'],
                'linea_prodotto': d['linea_prodotto'], 'descr_linea': d['descr_linea'],
                'stato': d['stato'], 'ean': d['ean'], 'tipoean': d['tipoean'],
                'giacenza_pdv': d['giacenza_pdv'], 'giacenza_deposito': d['giacenza_deposito'],
                'pracq': d['pracq'], 'iva': d['iva'],
                'descforn': d['descforn'], 'codartfo': d['codartfo'],
            })
    else:
        articoli_list = list(articoli_query)
        giacenze_map = _bulk_giacenze(art.codart for art in articoli_list)
        for art in articoli_list:
            if art.codart in seen_codart:
                continue
            seen_codart.add(art.codart)
            giacenze = giacenze_map.get(art.codart)
            giacenza_pdv = giacenze.giacenza_pdv or 0 if giacenze else 0
            giacenza_dep = giacenze.giacenza_deposito or 0 if giacenze else 0
            articoli_data.append({
                'codart': art.codart, 'descrart': art.descrart,
                'sett': art.sett, 'rep': art.rep, 'srep': art.srep,
                'fam': art.fam, 'ccom': art.ccom,
                'linea_prodotto': art.linea_prodotto, 'descr_linea': art.descr_linea,
                'stato': art.stato, 'ean': art.ean, 'tipoean': art.tipoean,
                'giacenza_pdv': float(giacenza_pdv) if giacenza_pdv else 0,
                'giacenza_deposito': float(giacenza_dep) if giacenza_dep else 0,
                'pracq': float(art.pracq) if art.pracq else 0,
                'iva': float(art.iva) if art.iva else 0,
                'descforn': art.descforn, 'codartfo': art.codartfo,
            })

    # Genera il file Excel tramite la funzione di utilità
    excel_buffer = export_articoli_excel(articoli_data, filename='assortimenti', include_barcode=True)

    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    filename = f'assortimenti_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response

def report_bar(request):
    """
    Report specifico per il reparto BAR.
    Filtra gli articoli appartenenti alle famiglie BAR (codici fissi derivati
    dalla logica Access originale). Per alcune famiglie (8940, 8943, 8970)
    esclude gli articoli con EAN di lunghezza <= 3 (logica Access: Len([ean]) > 3).
    """
    from .excel_utils import export_report_reparti

    # Famiglie BAR (dalla logica Access)
    famiglie_bar = ['8979', '8940', '8943', '8970', '8971', '8942', '8962']

    articoli_query = MasterAssortimenti.objects.using('goldreport').filter(
        fam__in=famiglie_bar,
        fornprinc=1
    ).order_by('fam', 'descrfam', 'codart')

    articoli_list = list(articoli_query)
    giacenze_map = _bulk_giacenze(art.codart for art in articoli_list)
    articoli_data = []
    for art in articoli_list:
        # Filtro per lunghezza EAN (logica Access: Len([ean]) > 3 per alcune FAM)
        if art.fam in ['8940', '8943', '8970']:
            if not art.ean or len(str(art.ean)) <= 3:
                continue

        giacenze = giacenze_map.get(art.codart)
        giacenza_pdv = giacenze.giacenza_pdv if giacenze else 0

        articoli_data.append({
            'codart': art.codart,
            'descrart': art.descrart,
            'fam': art.fam,
            'descrfam': art.descrfam,
            'codartfo': art.codartfo,
            'stato': art.stato,
            'ean': art.ean,
            'tipoean': art.tipoean,
            'giacenza_pdv': float(giacenza_pdv) if giacenza_pdv else 0,
            'descforn': art.descforn,
        })

    # Export diretto in Excel senza passare per la vista HTML
    excel_buffer = export_report_reparti(articoli_data, tipo_reparto='BAR')

    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    filename = f'bar_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response

def report_inventario(request):
    """
    Report inventario (equivalente a r_StampaInv dell'applicazione Access originale).
    Mostra solo gli articoli con giacenza PDV o deposito maggiore di zero.
    Opzionalmente filtrato per CCOM. Supporta export Excel tramite parametro
    ?export=excel nella query string; altrimenti renderizza il template HTML.
    Limite: 300 articoli per performance.
    """
    ccom = request.GET.get('ccom', '')

    # Query articoli con giacenze (solo fornitore principale)
    articoli_query = MasterAssortimenti.objects.using('goldreport').filter(fornprinc=1)

    if ccom:
        articoli_query = articoli_query.filter(ccom=ccom)

    articoli_query = articoli_query.order_by('linea_prodotto', 'tipo_riordino', 'fam', 'codart')

    # Filtra solo articoli con giacenze > 0
    articoli_data = []
    articoli_list = list(articoli_query[:300])
    giacenze_map = _bulk_giacenze(art.codart for art in articoli_list)
    for art in articoli_list:
        giacenze = giacenze_map.get(art.codart)

        if giacenze:
            giacenza_pdv = giacenze.giacenza_pdv or 0
            giacenza_dep = giacenze.giacenza_deposito or 0

            # Includi solo articoli con almeno una giacenza positiva
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

    # Se richiesto export Excel, restituisce il file direttamente
    if request.GET.get('export') == 'excel':
        excel_buffer = export_report_inventario(articoli_data, ccom=ccom)

        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        filename = f'inventario_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    # Altrimenti renderizza la vista HTML del report
    context = {
        'articoli': articoli_data,
        'ccom': ccom,
    }

    return render(request, 'asso_articoli/report_inventario.html', context)


def report_reparto(request, tipo):
    """
    Report specifici per reparti (BAR, MACELLERIA).
    Equivalente alle query q_estrBar e q_estrMace dell'applicazione Access.

    Args:
        tipo: stringa 'bar' o 'macelleria' passata dall'URL.

    Applica le stesse famiglie per entrambi i reparti (logica Access originale).
    Supporta export Excel tramite parametro ?export=excel.
    """
    # Famiglie per reparto (dalla logica Access)
    FAMIGLIE = {
        'bar': ['8979', '8940', '8943', '8970', '8971', '8942', '8962'],
        'macelleria': ['8979', '8940', '8943', '8970', '8971', '8942', '8962'],
    }

    if tipo not in FAMIGLIE:
        return HttpResponse("Tipo reparto non valido", status=400)

    famiglie = FAMIGLIE[tipo]

    articoli_query = MasterAssortimenti.objects.using('goldreport').filter(
        fam__in=famiglie,
        fornprinc=1
    ).order_by('fam', 'codart')

    articoli_list = list(articoli_query)
    giacenze_map = _bulk_giacenze(art.codart for art in articoli_list)
    articoli_data = []
    for art in articoli_list:
        # Filtro per lunghezza EAN (logica Access: Len([ean]) > 3 per alcune FAM)
        if art.fam in ['8940', '8943', '8970']:
            if not art.ean or len(str(art.ean)) <= 3:
                continue

        giacenze = giacenze_map.get(art.codart)
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

    # Export Excel se richiesto dalla query string
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
    API per ottenere la lista dei CCOM disponibili (per funzionalità autocomplete).
    Accetta il parametro ?q= per filtrare per codice o descrizione.
    Restituisce al massimo 50 risultati ordinati per codice CCOM.
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

def export_excel_reparti_view(request):
    """
    Export Excel ridotto per i reparti (senza CCOM, Linea, Prezzo, IVA, Fornitore).
    Usa la funzione export_report_reparti che genera un formato semplificato
    rispetto all'export completo della segreteria.
    Stessi filtri della vista index; limite 500 articoli per performance.
    """
    from .excel_utils import export_report_reparti

    selected_ccom = request.GET.get('ccom', '')
    selected_rep = request.GET.get('rep', '')
    selected_srep = request.GET.get('srep', '')
    selected_fam = request.GET.get('fam', '')
    selected_linee = request.GET.getlist('linea')
    linea_1_filter = request.GET.get('linea1', '') == '1'
    selected_descr = request.GET.get('descr', '')
    selected_stato = request.GET.get('stato', '')
    codart_list_raw = request.GET.get('codart_list', '')
    ean_list_raw = request.GET.get('ean_list', '')
    codart_list = [c.strip() for c in codart_list_raw.split(',') if c.strip()] if codart_list_raw else []
    ean_list = [e.strip() for e in ean_list_raw.split(',') if e.strip()] if ean_list_raw else []

    # Costruisce query con gli stessi filtri dell'index
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

    articoli_query = _filtra_per_codici(articoli_query, codart_list, ean_list)
    if selected_descr:
        articoli_query = articoli_query.filter(descrart__icontains=selected_descr)
    if selected_stato:
        articoli_query = articoli_query.filter(stato=selected_stato)

    articoli_query = articoli_query.order_by('linea_prodotto', 'tipo_riordino', 'fam', 'codart')

    # Prepara dati per il formato ridotto (solo campi necessari per i reparti)
    articoli_data = []
    seen_codart = set()

    if selected_stato == 'con_ea':
        raw_rows = _query_masterdataall(
            selected_ccom, selected_rep, selected_srep, selected_fam,
            selected_descr, codart_list, ean_list,
        )
        giacenze_map = _bulk_giacenze(row['CODART'] for row in raw_rows)
        for row in raw_rows:
            if row['CODART'] in seen_codart:
                continue
            seen_codart.add(row['CODART'])
            d = _build_articolo_da_masterdata(row, giacenze_map.get(row['CODART']))
            articoli_data.append({
                'codart': d['codart'], 'descrart': d['descrart'],
                'fam': d['fam'], 'descrfam': d['descrfam'],
                'codartfo': d['codartfo'], 'stato': d['stato'],
                'ean': d['ean'], 'tipoean': d['tipoean'],
                'giacenza_pdv': d['giacenza_pdv'],
                'descforn': d['descforn'],
            })
    else:
        articoli_list = list(articoli_query)
        giacenze_map = _bulk_giacenze(art.codart for art in articoli_list)
        for art in articoli_list:
            if art.codart in seen_codart:
                continue
            seen_codart.add(art.codart)
            giacenze = giacenze_map.get(art.codart)
            giacenza_pdv = giacenze.giacenza_pdv or 0 if giacenze else 0
            articoli_data.append({
                'codart': art.codart, 'descrart': art.descrart,
                'fam': art.fam, 'descrfam': art.descrfam,
                'codartfo': art.codartfo, 'stato': art.stato,
                'ean': art.ean, 'tipoean': art.tipoean,
                'giacenza_pdv': float(giacenza_pdv) if giacenza_pdv else 0,
                'descforn': art.descforn,
            })

    # Genera Excel nel formato ridotto per reparti
    excel_buffer = export_report_reparti(articoli_data, tipo_reparto='Reparti')

    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    filename = f'reparti_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
