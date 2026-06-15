"""Scarico Promo Abbigliamento - URL Configuration"""
from django.urls import path
from . import views

app_name = 'caricopromo_abbig'

urlpatterns = [
    path('', views.abbig_home, name='home'),
    path('api/carica-articoli/', views.api_carica_articoli, name='api_carica_articoli'),
    path('api/toggle-selezione/', views.api_toggle_selezione, name='api_toggle_selezione'),
    path('api/seleziona-batch/', views.api_seleziona_batch, name='api_seleziona_batch'),
    path('api/accoda-promo/', views.api_accoda_promo, name='api_accoda_promo'),
    path('api/svuota-fase1/', views.api_svuota_fase1, name='api_svuota_fase1'),
    path('api/visualizza-inseriti/', views.api_visualizza_inseriti, name='api_visualizza_inseriti'),
    path('api/svuota-inseriti/', views.api_svuota_inseriti, name='api_svuota_inseriti'),
    path('api/importa-excel/', views.api_importa_excel, name='api_importa_excel'),
]