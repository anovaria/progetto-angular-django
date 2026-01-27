from django.contrib import admin
from .models import Attivita, Utente, Merchandiser, Slot, SlotFornitore, SlotIngressoUscita


@admin.register(Attivita)
class AttivitaAdmin(admin.ModelAdmin):
    list_display = ['id', 'descrizione']
    search_fields = ['descrizione']


@admin.register(Utente)
class UtenteAdmin(admin.ModelAdmin):
    list_display = ['id', 'cognome', 'nome', 'email', 'attivo']
    list_filter = ['attivo']
    search_fields = ['cognome', 'nome', 'email']


@admin.register(Merchandiser)
class MerchandiserAdmin(admin.ModelAdmin):
    list_display = ['id', 'cognome', 'nome', 'telefono', 'email', 'attivo']
    list_filter = ['attivo']
    search_fields = ['cognome', 'nome']


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'merchandiser', 'utente', 'data_inizio', 'data_fine', 'giorni_attivi']
    list_filter = ['utente', 'data_inizio']
    search_fields = ['merchandiser__cognome', 'merchandiser__nome']
    date_hierarchy = 'data_inizio'


@admin.register(SlotFornitore)
class SlotFornitoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'slot', 'agenzia', 'fornitore_id', 'attivita']
    list_filter = ['agenzia', 'attivita']


@admin.register(SlotIngressoUscita)
class SlotIngressoUscitaAdmin(admin.ModelAdmin):
    list_display = ['id', 'slot', 'data', 'ingresso_1', 'uscita_1', 'ingresso_2', 'uscita_2', 'ore_lavorate']
    list_filter = ['data']
    date_hierarchy = 'data'
