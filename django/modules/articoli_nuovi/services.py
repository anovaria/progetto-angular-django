from .models import ArticoliNuovi
from django.db.models import F
from modules.portal import ean_utils

def get_articoli_nuovi():
    queryset = ArticoliNuovi.objects.filter(
        settore='1',
        tipo_art=1,
        eanprinc=1,
        stato__in=['N', 'W'],
    ).exclude(
        giac_dep__isnull=True
    ).exclude(
        giac_dep=0
    )

    queryset = queryset.order_by(
        'cod_articolo',
        F('giac_pdv').asc(nulls_last=True),
        F('giac_dep').desc(nulls_last=True),
    )

    articoli_dedup = []
    codici_visti = set()
    for articolo in queryset:
        if articolo.cod_articolo in codici_visti:
            continue
        codici_visti.add(articolo.cod_articolo)
        articoli_dedup.append(articolo)

    for articolo in articoli_dedup:
        tipo = int(articolo.tipo_ean) if articolo.tipo_ean is not None else None
        ean_calcolato = ean_utils.calcola_ean13(articolo.ean, tipo)
        articolo.ean_13 = ean_calcolato if ean_calcolato else articolo.ean
        articolo.barcode_valido = ean_calcolato is not None


    return articoli_dedup