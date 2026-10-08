from django.contrib import admin
from .models import Prenotazione


@admin.register(Prenotazione)
class PrenotazioneAdmin(admin.ModelAdmin):
    list_display = ['camera', 'cognome', 'nome', 'azienda', 'data_arrivo', 'data_partenza']