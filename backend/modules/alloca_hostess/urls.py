from django.urls import path
from . import views

app_name = 'alloca_hostess'

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
]
