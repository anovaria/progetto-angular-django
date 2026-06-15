from django.urls import path
from . import views

app_name = 'pallet_promoter'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    
    # Assegnazioni Pallet
    path('pallet/', views.pallet_list, name='pallet_list'),
    path('pallet/<int:periodo_id>/', views.pallet_griglia, name='pallet_griglia'),
    
    # Assegnazioni Testate
    path('testate/', views.testate_list, name='testate_list'),
    path('testate/<int:anno>/<int:mese>/', views.testate_griglia, name='testate_griglia'),
    
    # Hostess
    path('hostess/', views.hostess_planning, name='hostess_planning'),
    path('hostess/scelta-fornitore/', views.scelta_fornitore_hostess, name='scelta_fornitore_hostess'),
    path('presenze/', views.presenze_list, name='presenze_list'),
    
    # API per HTMX
    path('api/assegna-pallet/', views.assegna_pallet, name='assegna_pallet'),
    path('api/assegna-testata/', views.assegna_testata, name='assegna_testata'),
    path('api/cerca-fornitore/', views.cerca_fornitore, name='cerca_fornitore'),
    path('api/salva-presenza/', views.salva_presenza_hostess, name='salva_presenza'),
    path('api/salva-presenze/', views.salva_tutte_presenze, name='salva_presenze'),
    path('api/salva-fornitore-slot/', views.salva_fornitore_slot, name='salva_fornitore_slot'),
]
