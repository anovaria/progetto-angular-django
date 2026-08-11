from decimal import Decimal
from .models import Ean


def estrai_barcode(raw: str) -> str | None:
    """
    Replica la logica della macro VBA: salta i caratteri iniziali non numerici,
    raccoglie le cifre fino al primo separatore (qualunque esso sia),
    e ne restituisce le ultime 13.
    """
    s = raw.strip()
    while s and not s[0].isdigit():
        s = s[1:]

    digits = ''
    for ch in s:
        if ch.isdigit():
            digits += ch
        else:
            break

    if len(digits) >= 13:
        return digits[-13:]
    return None


def risolvi_articolo(ean13: str) -> dict:
    """
    Replica la logica delle colonne H/K/L/M/N del foglio Ortofrutta.
    Ritorna un dict con codart, descrart, gest, peso_num — sempre presenti
    (stringa vuota / None se l'articolo non è stato trovato).
    """
    f1_ean = ean13[:7]
    riga = Ean.objects.filter(EAN__startswith=f1_ean).first()
    gest = riga.GEST if riga else ''

    if gest == 'Kilogrammi':
        peso_grammi = int(ean13[7:12])
        return {
            'codart': riga.CODART if riga else '',
            'descrart': riga.DESCRART if riga else '',
            'gest': gest,
            'peso_num': Decimal(peso_grammi) / Decimal(1000),
        }
    else:
        articolo = Ean.objects.filter(EAN=ean13).first()
        return {
            'codart': articolo.CODART if articolo else '',
            'descrart': articolo.DESCRART if articolo else '',
            'gest': gest,
            'peso_num': None,
        }