"""Scarico Promo - URL Configuration"""
from django.urls import path
from . import views

app_name = 'scaricopromo'

urlpatterns = [
    # Dashboard principale (replica M_esporta)
    path('', views.dashboard, name='dashboard'),

    # Gestione "Mettere in X"
    path('mettere/<str:stato>/', views.mettere_in, name='mettere_in'),
    path('mettere/<str:stato>/elimina/<int:pk>/', views.elimina_articolo, name='elimina_articolo'),

    # Azioni (pulsanti M_esporta)
    path('azione/valida-a/', views.azione_valida_a, name='azione_valida_a'),
    path('azione/crea-attributi/', views.azione_crea_attributi, name='azione_crea_attributi'),
    path('azione/esporta-csv/', views.azione_esporta_csv, name='azione_esporta_csv'),

    # Report
    path('report/non-posso-a/', views.report_non_posso, name='report_non_posso'),

    # API
    path('api/conteggi/', views.api_conteggi, name='api_conteggi'),
]
