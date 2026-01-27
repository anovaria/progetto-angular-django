"""
URL Configuration per app AssoArticoli
"""
from django.urls import path
from . import views

app_name = 'asso_articoli'

urlpatterns = [
    # Maschera principale
    path('', views.index, name='index'),
    
    # Export Excel
    path('export/excel/', views.export_excel_view, name='export_excel'),
    
    # Report inventario
    path('report/inventario/', views.report_inventario, name='report_inventario'),
    
    # Report reparti
    path('report/reparto/<str:tipo>/', views.report_reparto, name='report_reparto'),
    
    # API
    path('api/ccom/', views.api_ccom_list, name='api_ccom_list'),
]
