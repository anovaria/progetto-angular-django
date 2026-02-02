"""
URL patterns per l'app Welfare
"""

from django.urls import path
from . import views

app_name = 'welfare'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Ricerca voucher
    path('ricerca/', views.ricerca_voucher, name='ricerca_voucher'),
    
    # Cassa
    path('cassa/', views.cassa_consegna, name='cassa_consegna'),
    path('da-consegnare/', views.lista_da_consegnare, name='lista_da_consegnare'),
    path('storico/', views.storico_consegne, name='storico_consegne'),
    
    # Contabilità
    path('contabilita/', views.contabilita, name='contabilita'),
    path('contabilita/export/', views.report_mensile_excel, name='report_excel'),
    
    # Import Email
    path('import/', views.import_email, name='import_email'),
    path('import/valida/<int:pk>/', views.valida_provvisoria, name='valida_provvisoria'),
    path('import/elimina/<int:pk>/', views.elimina_provvisoria, name='elimina_provvisoria'),
    
    # API JSON
    path('api/cerca/', views.api_cerca_voucher, name='api_cerca'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
