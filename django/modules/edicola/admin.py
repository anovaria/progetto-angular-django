from django.contrib import admin

from .models import EdicolaLog, EdicolaPrincipale, SalvaPrinc


@admin.register(EdicolaPrincipale)
class EdicolaPrincipaleAdmin(admin.ModelAdmin):
    list_display = ("codart", "descrart", "ean", "eanprinc", "giacenza_pdv", "prezzovend", "dtaaggio", "data")
    search_fields = ("codart", "descrart", "ean")
    list_filter = ("eanprinc",)


@admin.register(SalvaPrinc)
class SalvaPrincAdmin(admin.ModelAdmin):
    list_display = ("codart", "ean", "eanprinc", "data")
    search_fields = ("codart", "ean")


@admin.register(EdicolaLog)
class EdicolaLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "message")
    list_filter = ("level",)
    search_fields = ("message", "details")
