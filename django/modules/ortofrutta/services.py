from decimal import Decimal
from .models import Ean,ScansioneOrtofrutta,ListinoGiorno
from django.db.models import Sum

def totali_con_prezzo(solo_con_prezzo=True):
    totali = (
    ScansioneOrtofrutta.objects
    .filter(data_competenza__isnull=False, fatturato=False)
    .values('data_competenza', 'codart')
    .annotate(totale_peso=Sum('peso_num'), totale_qta=Sum('qta'))
    .order_by('data_competenza', 'codart')
    )
    codarts = [riga['codart'] for riga in totali]
    articoli = {a.CODART: a for a in Ean.objects.filter(CODART__in=codarts)}
    prezzi = {(p.codart, p.data_competenza): p for p in ListinoGiorno.objects.filter(codart__in=codarts)}
    for riga in totali:
        articolo = articoli.get(riga['codart'])
        riga['descrart'] = articolo.DESCRART if articolo else ''
        riga['gest'] = articolo.GEST if articolo else ''
        prezzo = prezzi.get((riga['codart'], riga['data_competenza']))
        riga['prezzo_listino'] = str(prezzo.prezzo_listino) if prezzo else ''
        quantita = riga['totale_peso'] if riga['totale_peso'] is not None else riga['totale_qta']
        riga['quantita'] = quantita
        if prezzo and quantita is not None:
            riga['valore'] = quantita * prezzo.prezzo_listino
        else:
            riga['valore'] = None
    if solo_con_prezzo:
        return [riga for riga in totali if riga['prezzo_listino'] != '']
    return list(totali)

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