from django.contrib import admin
from .models import (
    MettereInA, MettereInE, MettereInF, MettereInI, MettereInK, MettereInS,
    NonPossoMettereInA, ChiudiAttri, ApriAttri, AggiornaAttri,
    PerExport, PerExportStorico,
)


@admin.register(MettereInA)
class MettereInAAdmin(admin.ModelAdmin):
    list_display = ('codart', 'ccom')
    search_fields = ('codart',)


@admin.register(MettereInE)
class MettereInEAdmin(admin.ModelAdmin):
    list_display = ('codart',)
    search_fields = ('codart',)


@admin.register(PerExport)
class PerExportAdmin(admin.ModelAdmin):
    list_display = ('CodiceProdotto', 'DescrizioneProdotto', 'DataInizio', 'DataFine', 'ScontoExtra')
    search_fields = ('CodiceProdotto', 'DescrizioneProdotto')


@admin.register(PerExportStorico)
class PerExportStoricoAdmin(admin.ModelAdmin):
    list_display = ('CodiceProdotto', 'DescrizioneProdotto', 'DATAEXPORT', 'utenteWind')
    search_fields = ('CodiceProdotto',)
    list_filter = ('DATAEXPORT', 'utenteWind')


@admin.register(AggiornaAttri)
class AggiornaAttriAdmin(admin.ModelAdmin):
    list_display = ('CodArticolo', 'ClasseAttri', 'CodAttri', 'dtaini', 'dtaFine')
    search_fields = ('CodArticolo',)
