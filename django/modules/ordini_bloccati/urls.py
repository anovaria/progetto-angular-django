from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='ordini_bloccati_main'),
    path('export/', views.export_excel, name='ordini_bloccati_export'),
]
