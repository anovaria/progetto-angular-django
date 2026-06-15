import json
from decimal import Decimal, InvalidOperation

from django.db import connections
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Ricetta, RicettaIngrediente, RicettaImballo


def _username(request):
    return request.session.get('user', {}).get('username', 'anonimo')


def _dec(val, default=None):
    if val is None or val == '':
        return default
    try:
        return Decimal(str(val).replace(',', '.'))
    except InvalidOperation:
        return default


# ── Lista ─────────────────────────────────────────────────────────────────────

def ricette_list(request):
    q = request.GET.get('q', '').strip()
    qs = Ricetta.objects.prefetch_related('ingredienti', 'imballaggi')
    if q:
        qs = qs.filter(descrizione__icontains=q) | qs.filter(codice_articolo__icontains=q) | qs.filter(categoria__icontains=q)
    ricette = list(qs.order_by('descrizione'))
    return render(request, 'ricette/list.html', {'ricette': ricette, 'q': q})


# ── Dettaglio ─────────────────────────────────────────────────────────────────

def ricetta_detail(request, pk):
    ricetta = get_object_or_404(Ricetta.objects.prefetch_related('ingredienti', 'imballaggi'), pk=pk)
    return render(request, 'ricette/detail.html', {'ricetta': ricetta})


# ── Create / Edit ─────────────────────────────────────────────────────────────

def _salva_ricetta(request, ricetta=None):
    p = request.POST
    is_new = ricetta is None

    if is_new:
        ricetta = Ricetta()
        ricetta.creato_da = _username(request)

    ricetta.codice_articolo        = p.get('codice_articolo', '').strip()
    ricetta.descrizione            = p.get('descrizione', '').strip()
    ricetta.categoria              = p.get('categoria', '').strip()
    ricetta.difficolta             = p.get('difficolta', 'media')
    ricetta.ean                    = p.get('ean', '').strip()
    ricetta.tipo_contenitore       = p.get('tipo_contenitore', '').strip()
    ricetta.dimensioni_contenitore = p.get('dimensioni_contenitore', '').strip()
    ricetta.grammatura_media_kg    = _dec(p.get('grammatura_media_kg'))
    ricetta.shelf_life             = p.get('shelf_life', '').strip()
    ricetta.conservabilita         = p.get('conservabilita', '').strip()
    ricetta.kcal                   = _dec(p.get('kcal'))
    ricetta.protidi                = _dec(p.get('protidi'))
    ricetta.lipidi                 = _dec(p.get('lipidi'))
    ricetta.glucidi                = _dec(p.get('glucidi'))
    ricetta.calo_peso_pct          = _dec(p.get('calo_peso_pct'))
    ricetta.quantita_prodotta_kg   = _dec(p.get('quantita_prodotta_kg'))
    ricetta.porzione_media_kg      = _dec(p.get('porzione_media_kg'))
    ricetta.tempo_produzione_min   = _dec(p.get('tempo_produzione_min'))
    ricetta.costo_al_minuto        = _dec(p.get('costo_al_minuto'))
    ricetta.prezzo_vendita_iva     = _dec(p.get('prezzo_vendita_iva'))
    ricetta.aliquota_iva           = _dec(p.get('aliquota_iva'))
    ricetta.ingredienti_etichetta  = p.get('ingredienti_etichetta', '').strip()
    ricetta.modalita_preparazione  = p.get('modalita_preparazione', '').strip()
    ricetta.abbinamenti            = p.get('abbinamenti', '').strip()
    ricetta.consigli_cottura       = p.get('consigli_cottura', '').strip()
    ricetta.note                   = p.get('note', '').strip()
    ricetta.save()

    if not is_new:
        ricetta.ingredienti.all().delete()
        ricetta.imballaggi.all().delete()

    ing_data = json.loads(p.get('ingredienti_json', '[]'))
    for i, row in enumerate(ing_data):
        if not row.get('descrizione', '').strip():
            continue
        RicettaIngrediente.objects.create(
            ricetta=ricetta,
            ordine=i,
            codice=row.get('codice', '').strip(),
            descrizione=row.get('descrizione', '').strip(),
            pct_cp_scarto=_dec(row.get('pct_cp_scarto'), Decimal('0')),
            um=row.get('um', 'kg').strip() or 'kg',
            peso_qta=_dec(row.get('peso_qta')),
            pa_senza_iva=_dec(row.get('pa_senza_iva')),
        )

    imb_data = json.loads(p.get('imballaggi_json', '[]'))
    for i, row in enumerate(imb_data):
        if not row.get('descrizione', '').strip():
            continue
        RicettaImballo.objects.create(
            ricetta=ricetta,
            ordine=i,
            codice=row.get('codice', '').strip(),
            descrizione=row.get('descrizione', '').strip(),
            um=row.get('um', 'pz').strip() or 'pz',
            quantita=_dec(row.get('quantita')),
            pa_senza_iva=_dec(row.get('pa_senza_iva')),
        )

    return ricetta


def _form_context(ricetta):
    if ricetta is None:
        return {'ricetta': None, 'ingredienti_json': '[]', 'imballaggi_json': '[]'}
    ing = [
        {'codice': i.codice, 'descrizione': i.descrizione, 'um': i.um,
         'pct_cp_scarto': str(i.pct_cp_scarto or ''),
         'peso_qta': str(i.peso_qta or ''), 'pa_senza_iva': str(i.pa_senza_iva or '')}
        for i in ricetta.ingredienti.all()
    ]
    imb = [
        {'codice': i.codice, 'descrizione': i.descrizione, 'um': i.um,
         'quantita': str(i.quantita or ''), 'pa_senza_iva': str(i.pa_senza_iva or '')}
        for i in ricetta.imballaggi.all()
    ]
    return {
        'ricetta': ricetta,
        'ingredienti_json': json.dumps(ing),
        'imballaggi_json':  json.dumps(imb),
    }


def ricetta_create(request):
    if request.method == 'POST':
        ricetta = _salva_ricetta(request)
        return redirect('ricette:detail', pk=ricetta.pk)
    return render(request, 'ricette/form.html', _form_context(None))


def ricetta_edit(request, pk):
    ricetta = get_object_or_404(Ricetta.objects.prefetch_related('ingredienti', 'imballaggi'), pk=pk)
    if request.method == 'POST':
        _salva_ricetta(request, ricetta)
        return redirect('ricette:detail', pk=ricetta.pk)
    return render(request, 'ricette/form.html', _form_context(ricetta))


# ── Delete ────────────────────────────────────────────────────────────────────

@require_POST
def ricetta_delete(request, pk):
    ricetta = get_object_or_404(Ricetta, pk=pk)
    ricetta.delete()
    return redirect('ricette:list')


# ── API autocomplete articoli (legge da Db_Category) ─────────────────────────

def api_search_articoli(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    pattern = f'%{q}%'
    sql = """
        SELECT TOP 25
            CODART, DESCRART, DESCR_REPARTO, DESCR_FAMIGLIA,
            NETTONETTODash, VARACQ
        FROM dbo.t_masterdataCategory
        WHERE (CODART LIKE %s OR DESCRART LIKE %s)
        ORDER BY DESCRART
    """
    try:
        with connections['category'].cursor() as cursor:
            cursor.execute(sql, [pattern, pattern])
            cols = [c[0] for c in cursor.description]
            rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception:
        return JsonResponse({'results': []})

    results = []
    seen = set()
    for r in rows:
        codart = r.get('CODART') or ''
        if codart in seen:
            continue
        seen.add(codart)
        pa = r.get('NETTONETTODash') or r.get('VARACQ') or 0
        results.append({
            'codart':   codart,
            'descrart': r.get('DESCRART') or '',
            'reparto':  r.get('DESCR_REPARTO') or '',
            'famiglia': r.get('DESCR_FAMIGLIA') or '',
            'pa':       float(pa) if pa else 0,
        })

    return JsonResponse({'results': results})
