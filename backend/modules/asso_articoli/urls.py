"""
URL configuration per app AssoArticoli
"""
from django.urls import path
from . import views

app_name = 'asso_articoli'

urlpatterns = [
    # Maschera principale
    path('', views.index, name='index'),
    
    # Export Excel
    path('export/excel/', views.export_excel_view, name='export_excel'),
    
    # Report
    path('report/inventario/', views.report_inventario, name='report_inventario'),
    path('report/reparto/<str:tipo>/', views.report_reparto, name='report_reparto'),
    path('export/excel/reparti/', views.export_excel_reparti_view, name='export_excel_reparti'),
    path('report/bar/', views.report_bar, name='report_bar'),
    
    # API
    path('api/ccom/', views.api_ccom_list, name='api_ccom'),
    path('api/linee/', views.api_linee_per_ccom, name='api_linee'),  # NUOVA API per linee filtrate per CCOM
]
