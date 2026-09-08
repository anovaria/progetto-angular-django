"""Scarico Promo Reparto - URL Configuration"""
from django.urls import path
from . import views

app_name = 'caricopromo-reparto'

urlpatterns = [
    path('', views.reparto_home, name='home'),
    path('api/carica-articoli/', views.api_carica_articoli, name='api_carica_articoli'),
    path('api/toggle-selezione/', views.api_toggle_selezione, name='api_toggle_selezione'),
    path('api/seleziona-batch/', views.api_seleziona_batch, name='api_seleziona_batch'),
    path('api/accoda-promo/', views.api_accoda_promo, name='api_accoda_promo'),
    path('api/svuota-fase1/', views.api_svuota_fase1, name='api_svuota_fase1'),
    path('api/visualizza-inseriti/', views.api_visualizza_inseriti, name='api_visualizza_inseriti'),
    path('api/svuota-inseriti/', views.api_svuota_inseriti, name='api_svuota_inseriti'),
    path('api/rimuovi-inserito/', views.api_rimuovi_inserito, name='api_rimuovi_inserito'),
    path('api/importa-excel-svendita/', views.api_importa_excel_svendita, name='api_importa_excel_svendita'),
    path('api/cerca-barcode/', views.api_cerca_barcode, name='api_cerca_barcode'),
    path('api/aggiungi-manuali/', views.api_aggiungi_manuali, name='api_aggiungi_manuali'),
    path('api/duplica/promos/', views.api_duplica_get_promos, name='api_duplica_get_promos'),
    path('api/duplica/ccom/', views.api_duplica_get_ccom, name='api_duplica_get_ccom'),
    path('api/duplica/articoli/', views.api_duplica_get_articoli, name='api_duplica_get_articoli'),
    path('api/duplica/inserisci/', views.api_duplica_inserisci, name='api_duplica_inserisci'),
]