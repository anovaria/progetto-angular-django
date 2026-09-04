from .models import ArticoliNuovi
from django.db.models import F

def get_articoli_nuovi():
    queryset = ArticoliNuovi.objects.filter(
        settore='1',
        tipoean=1,
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

    return articoli_dedup