from django.contrib import admin
from .models import (
    Ruolo, Utente, TaglioBuono, RichiestaWelfare,
    DettaglioBuono, RichiestaProvvisoria, EmailImportata,
    VerificaEudaimon
)


@admin.register(Ruolo)
class RuoloAdmin(admin.ModelAdmin):
    list_display = ['id_ruolo', 'descrizione']
    ordering = ['id_ruolo']


@admin.register(Utente)
class UtenteAdmin(admin.ModelAdmin):
    list_display = ['username', 'ruolo', 'data_login', 'volte']
    list_filter = ['ruolo']
    search_fields = ['username']


@admin.register(TaglioBuono)
class TaglioBuonoAdmin(admin.ModelAdmin):
    list_display = ['valore_nominale', 'attivo']
    ordering = ['valore_nominale']


class DettaglioBuonoInline(admin.TabularInline):
    model = DettaglioBuono
    extra = 0


@admin.register(RichiestaWelfare)
class RichiestaWelfareAdmin(admin.ModelAdmin):
    list_display = ['num_richiesta', 'nominativo', 'nome_mittente', 'stato', 'totale_buono', 'data_consegna']
    list_filter = ['stato', 'data_consegna']
    search_fields = ['num_richiesta', 'nominativo', 'nome_mittente']
    date_hierarchy = 'data_creazione'
    inlines = [DettaglioBuonoInline]
    readonly_fields = ['data_importazione']


@admin.register(RichiestaProvvisoria)
class RichiestaProvvisoriaAdmin(admin.ModelAdmin):
    list_display = ['num_richiesta', 'nominativo', 'totale_buono', 'processato', 'data_importazione']
    list_filter = ['processato']
    search_fields = ['num_richiesta', 'nominativo']


@admin.register(EmailImportata)
class EmailImportataAdmin(admin.ModelAdmin):
    list_display = ['oggetto', 'sender_address', 'ricevuto_il', 'elaborata']
    list_filter = ['elaborata']
    search_fields = ['oggetto', 'sender_address']
    date_hierarchy = 'ricevuto_il'


@admin.register(VerificaEudaimon)
class VerificaEudaimonAdmin(admin.ModelAdmin):
    list_display = ['numero_richiesta', 'nominativo_dipendente', 'importo', 'stato']
    search_fields = ['numero_richiesta', 'nominativo_dipendente']
