from django.urls import path
from . import views

app_name = 'merchandiser'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    
    # Anagrafiche
    path('merchandiser/', views.merchandiser_list, name='merchandiser_list'),
    path('attivita/', views.attivita_list, name='attivita_list'),
    path('utenti/', views.utenti_list, name='utenti_list'),
    path('agenzie/', views.agenzie_list, name='agenzie_list'),
    
    # Slot
    path('slot/', views.slot_list, name='slot_list'),
    path('slot/<int:slot_id>/', views.slot_detail, name='slot_detail'),
    
    # Solo Orari (Punto Info)
    path('solo-orari/', views.solo_orari, name='solo_orari'),
    
    # API
    path('api/salva-orario/', views.salva_orario, name='salva_orario'),
    path('api/cerca-fornitore/', views.cerca_fornitore, name='cerca_fornitore'),
    path('api/salva-slot-fornitore/', views.salva_slot_fornitore, name='salva_slot_fornitore'),
    path('api/elimina-slot-fornitore/<int:sf_id>/', views.elimina_slot_fornitore, name='elimina_slot_fornitore'),
]
