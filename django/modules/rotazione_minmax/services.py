from .models import RotazForn3

# Ordine delle colonne come nell'Excel
CAMPI = (
    'sito', 'sett', 'rep', 'srep', 'fam', 'descrfam', 'foprinc', 'ordinabile',
    'codforn', 'ccom', 'descrccom', 'descr_linea', 'corsia', 'campata', 'facing',
    'min_qta', 'max_qta', 'qtamax', 'rotanooff', 'rotaoff', 'pzxcart',
    'codarticolo', 'descrart', 'ean', 'stato', 'pick', 'baricentro', 'dtaaggio',
    'giacenza_pdv', 'giacenza_deposito',
)

# Stringhe in Gold, numeri nell'Excel (conversione di Power Query)
CAMPI_INT = (
    'sett', 'rep', 'srep', 'fam', 'codforn', 'ccom', 'codarticolo',
    'corsia', 'campata', 'facing', 'min_qta', 'max_qta',
)

# numeric(n,0) -> il driver restituisce Decimal
CAMPI_DECIMAL = ('sito', 'foprinc')

def _to_int(val):
    if val is None or val =='':
        return None
    try:
        return int(val)
    except ValueError:
        return val

def _base_qs():
    return RotazForn3.objects.exclude(stato='L')

def elenco_siti():
    qs = _base_qs().values_list('sito', flat=True).distinct().order_by('sito')
    return [int(s) for s in qs]

def righe_rotazione(sito):
    qs = _base_qs().filter(sito=sito).values(*CAMPI).distinct()
    righe = []
    for r in qs:
        for k, v in r.items():
            if isinstance(v, str):
                r[k] = v.strip()
        for k in CAMPI_INT:
            r[k] = _to_int(r[k])
        for k in CAMPI_DECIMAL:
            r[k]= int(r[k]) if r[k] is not None else None
        righe.append(r)
    return righe