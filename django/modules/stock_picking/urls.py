from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='stock_picking_main'),
    path('export/', views.export_excel, name='stock_picking_export'),
    path('filtri/', views.filtri_json, name='stock_picking_filtri'),
]
