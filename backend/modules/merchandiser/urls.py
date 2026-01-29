from django.urls import path
from . import views

app_name = 'merchandiser'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    
        # Merchandiser
    path('merchandiser/', views.merchandiser_list, name='merchandiser_list'),
    path('merchandiser/add/', views.merchandiser_add, name='merchandiser_add'),
    path('merchandiser/<int:merchandiser_id>/edit/', views.merchandiser_edit, name='merchandiser_edit'),
    path('merchandiser/<int:merchandiser_id>/delete/', views.merchandiser_delete, name='merchandiser_delete'),
    # Hostess
    path('hostess/', views.hostess_list, name='hostess_list'),
    path('hostess/add/', views.hostess_add, name='hostess_add'),
    path('hostess/<int:hostess_id>/edit/', views.hostess_edit, name='hostess_edit'),
    path('hostess/<int:hostess_id>/delete/', views.hostess_delete, name='hostess_delete'),

    path('attivita/', views.attivita_list, name='attivita_list'),
    path('utenti/', views.utenti_list, name='utenti_list'),
    path('agenzie/', views.agenzie_list, name='agenzie_list'),
    
    # Slot
    path('slot/', views.slot_list, name='slot_list'),
    path('slot/<int:slot_id>/', views.slot_detail, name='slot_detail'),
    path('api/salva-note-slot/', views.salva_note_slot, name='salva_note_slot'),
    
    # Solo Orari (Punto Info)
    path('solo-orari/', views.solo_orari, name='solo_orari'),
    
    # API
    path('api/salva-orario/', views.salva_orario, name='salva_orario'),
    path('api/cerca-fornitore/', views.cerca_fornitore, name='cerca_fornitore'),
    path('api/salva-slot-fornitore/', views.salva_slot_fornitore, name='salva_slot_fornitore'),
    path('api/elimina-slot-fornitore/<int:sf_id>/', views.elimina_slot_fornitore, name='elimina_slot_fornitore'),
]
