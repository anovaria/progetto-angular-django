from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='picking_negativi_main'),
    path('export/', views.export_excel, name='picking_negativi_export'),
]
