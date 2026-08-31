from .models import VLuke
TEXT_FILTERS = {
    'reparto': 'descr_reparto__icontains',
    'cod_articolo': 'cod_articolo__icontains',
    'descr_articolo': 'descr_articolo__icontains', 
    'settore': 'descr_settore__icontains', 
    'stato': 'stato__icontains',
    'corsia': 'corsia__icontains', 
    'campata': 'campata__icontains'
}
SORTABLE_COLUMNS = {
    'reparto': 'reparto',
    'descr_reparto': 'descr_reparto',
    'corsia':'corsia',
    'campata':'campata',
    'cod_articolo':'cod_articolo',
    'descr_articolo':'descr_articolo',
    'stato':'stato',
    'giac_pdv':'giac_pdv',
    'ultima_vendita':'ultima_vendita',
    'giac_dep':'giac_dep',   
}
def get_giacenze_negative(get_params):
    righe = VLuke.objects.filter(giac_pdv__lt=0)
    for param, lookup in TEXT_FILTERS.items():
        valore = get_params.get(param, '')
        if valore:
            righe = righe.filter(**{lookup: valore})
    direzione = get_params.get('dir', 'asc')
    sort = get_params.get('sort', '')

    return righe