from django.shortcuts import render
from .services import get_giacenze_negative,TEXT_FILTERS

COLONNE = [
    ('reparto', 'Reparto'),
    ('descr_reparto', 'Descrizione Reparto'),
    ('corsia', 'Corsia'),
    ('campata', 'Campata'),
    ('cod_articolo', 'Codice Articolo'),
    ('descr_articolo', 'Descrizione Articolo'),
    ('stato', 'Stato'),
    ('giac_pdv', 'Giacenza PDV'),
    ('ultima_vendita', 'Ultima Vendita'),
    ('giac_dep', 'Giacenza Deposito'),
]

def main(request):
    righe = get_giacenze_negative(request.GET)
    filters = {}
    filters['sort'] = request.GET.get('sort', '')
    filters['dir'] = request.GET.get('dir', 'asc')
    for param in TEXT_FILTERS:
        filters[param] = request.GET.get(param, '')
    ctx = {
        'colonne': COLONNE,
        'righe': righe,
        'totale': len(righe),
        'filters': filters,
    }

    return render(request, 'giacenze_negative/main.html', ctx)
