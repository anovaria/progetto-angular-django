from .models import VLuke
from datetime import datetime

TEXT_FILTERS = {
    'reparto': 'descr_reparto__icontains',
    'cod_articolo': 'cod_articolo__icontains',
    'descr_articolo': 'descr_articolo__icontains',
    'settore': 'descr_settore__icontains',
    'stato': 'stato__icontains',
    'corsia': 'corsia__icontains',
    'campata': 'campata__icontains',
}

SORTABLE_COLUMNS = {
    'reparto': 'reparto',
    'descr_reparto': 'descr_reparto',
    'cod_articolo': 'cod_articolo',
    'corsia': 'corsia',
    'campata': 'campata',
    'descr_articolo': 'descr_articolo',
    'stato': 'stato',
    'giac_pdv': 'giac_pdv',
    'ultima_vendita': 'ultima_vendita',
    'giac_dep': 'giac_dep',
}

def get_giacenze_negative(get_params):
    righe = VLuke.objects.filter(giac_pdv__lt=0)

    for param, lookup in TEXT_FILTERS.items():
        valore = get_params.get(param, '')
        if valore:
            righe = righe.filter(**{lookup: valore})

    direzione = get_params.get('dir', 'asc')
    sort = get_params.get('sort', '')

    if sort in SORTABLE_COLUMNS:     
        if sort == 'ultima_vendita':
            righe = sorted(righe, key=lambda riga: datetime.min if not riga.ultima_vendita else datetime.strptime(riga.ultima_vendita, '%d/%m/%Y'), reverse=(direzione == 'desc'))
        else:
            campo = SORTABLE_COLUMNS[sort]
            if direzione == 'desc':
                campo = '-' + campo
            righe = righe.order_by(campo)
    else:
        righe = righe.order_by('descr_reparto', '-ultima_vendita')

    return righe