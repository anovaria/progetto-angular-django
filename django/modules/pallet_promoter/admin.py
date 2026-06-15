from django.contrib import admin
from .models import (
    Agenzia, Reparto, Buyer, Fornitore, Hostess,
    Pallet, Testata, Periodo,
    AssegnazionePallet, AssegnazioneTestata,
    PianificazioneHostess, PresenzaHostess,
)


# ============================================
# ANAGRAFICHE
# ============================================

@admin.register(Agenzia)
class AgenziaAdmin(admin.ModelAdmin):
    list_display = ['id', 'descrizione', 'nota']
    search_fields = ['descrizione']


@admin.register(Reparto)
class RepartoAdmin(admin.ModelAdmin):
    list_display = ['id', 'descrizione']


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ['id', 'nominativo', 'codice_as400']
    search_fields = ['nominativo']


@admin.register(Fornitore)
class FornitoreAdmin(admin.ModelAdmin):
    list_display = ['codice', 'nome', 'buyer', 'reparto']
    search_fields = ['codice', 'nome']
    list_filter = ['reparto']


@admin.register(Hostess)
class HostessAdmin(admin.ModelAdmin):
    list_display = ['id', 'nominativo', 'ruolo', 'attiva', 'scadenza_libretto_sanitario']
    search_fields = ['nominativo']
    list_filter = ['attiva', 'ruolo']


# ============================================
# SPAZI
# ============================================

@admin.register(Pallet)
class PalletAdmin(admin.ModelAdmin):
    list_display = ['codice', 'buyer', 'dimensione']
    list_filter = ['buyer']


@admin.register(Testata)
class TestataAdmin(admin.ModelAdmin):
    list_display = ['id', 'locazione', 'bloccata']
    list_filter = ['bloccata']



# ============================================
# PERIODI
# ============================================

@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ['codice', 'descrizione', 'data_inizio', 'data_fine', 'anno']
    list_filter = ['anno']
    search_fields = ['codice', 'descrizione']


# ============================================
# ASSEGNAZIONI
# ============================================

@admin.register(AssegnazionePallet)
class AssegnazionePalletAdmin(admin.ModelAdmin):
    list_display = ['pallet', 'periodo', 'dettaglio', 'modificato_da']
    list_filter = ['periodo']
    search_fields = ['pallet__codice']

@admin.register(AssegnazioneTestata)
class AssegnazioneTestataAdmin(admin.ModelAdmin):
    list_display = ['testata', 'mese', 'anno', 'modificato_da']
    list_filter = ['anno', 'mese']
    search_fields = ['testata__locazione']


# ============================================
# HOSTESS
# ============================================

@admin.register(PianificazioneHostess)
class PianificazioneHostessAdmin(admin.ModelAdmin):
    list_display = ['giorno', 'slot', 'hostess', 'periodo']
    list_filter = ['periodo', 'giorno']
    date_hierarchy = 'giorno'


@admin.register(PresenzaHostess)
class PresenzaHostessAdmin(admin.ModelAdmin):
    list_display = ['giorno', 'slot', 'hostess', 'agenzia', 'tipo',
                    'ingresso_mattino', 'uscita_mattino',
                    'ingresso_pomeriggio', 'uscita_pomeriggio']
    list_filter = ['tipo', 'giorno']
    date_hierarchy = 'giorno'

