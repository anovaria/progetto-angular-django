from django.contrib import admin
from .models import ImportBatch, ImportRow, GoldTableSnapshot, IntermediateAggPrAcq, IntermediateAggiornaEan, IntermediateAggiornamentiVari


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ('filename', 'uploaded_at')
    date_hierarchy = 'uploaded_at'


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ('batch', 'line_number', 'cod_art_fo', 'descrizione_articolo', 'ean')
    list_filter = ('batch',)


@admin.register(GoldTableSnapshot)
class GoldTableSnapshotAdmin(admin.ModelAdmin):
    list_display = ('source_table', 'id', 'synced_at')
    list_filter = ('source_table',)
    date_hierarchy = 'synced_at'


@admin.register(IntermediateAggPrAcq)
class IntermediateAggPrAcqAdmin(admin.ModelAdmin):
    list_display = ('batch', 'cod_art_fo', 'codart', 'az', 'ros_pracq', 'cidac_prezzo', 'rep', 'srep', 'ccom')
    search_fields = ('cod_art_fo', 'codart', 'descrart')
    list_filter = ('rep', 'srep', 'ccom')


@admin.register(IntermediateAggiornaEan)
class IntermediateAggiornaEanAdmin(admin.ModelAdmin):
    list_display = ('batch', 'cod_art_fo', 'ean', 'codart')
    search_fields = ('cod_art_fo', 'ean', 'descrizione_articolo')


@admin.register(IntermediateAggiornamentiVari)
class IntermediateAggiornamentiVariAdmin(admin.ModelAdmin):
    list_display = ('batch', 'cod_art_fo', 'codart', 'agg_pz_x_crt', 'agg_crt_x_str', 'agg_str_x_plt')
    search_fields = ('cod_art_fo', 'codart', 'descrizione_articolo', 'ean')
