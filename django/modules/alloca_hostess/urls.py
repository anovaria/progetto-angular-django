from django.urls import path
from . import views

app_name = 'alloca-hostess'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    
    # Anagrafiche
    path('hostess/', views.hostess_list, name='hostess_list'),
    path('agenzie/', views.agenzie_list, name='agenzie_list'),
    
    # Individuazione Hostess (form principale)
    path('individuazione/', views.individuazione, name='individuazione'),
    
    # API
    path('api/cerca-fornitore/', views.cerca_fornitore, name='cerca_fornitore'),
    path('api/salva-presenze/', views.salva_presenze, name='salva_presenze'),
    # Orari Hostess
    path('orari-hostess/', views.orari_hostess, name='orari_hostess'),
    path('api/salva-orario-hostess/', views.salva_orario_hostess, name='salva_orario_hostess'),
    # Attività non previste
    path('attivita-non-previste/', views.attivita_non_previste, name='attivita_non_previste'),
    path('api/cerca-nominativo-polmone/', views.cerca_nominativo_polmone, name='cerca_nominativo_polmone'),
    path('api/aggiungi-nominativo-polmone/', views.aggiungi_nominativo_polmone, name='aggiungi_nominativo_polmone'),
    path('api/salva-attivita-non-prevista/', views.salva_attivita_non_prevista, name='salva_attivita_non_prevista'),
    path('api/elimina-attivita-non-prevista/', views.elimina_attivita_non_prevista, name='elimina_attivita_non_prevista'),
    path('api/salva-orario-attivita/', views.salva_orario_attivita, name='salva_orario_attivita'),
    path('api/copia-slot/', views.copia_slot, name='copia_slot'),
]

