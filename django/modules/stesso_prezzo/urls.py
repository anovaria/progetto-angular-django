from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='stesso_prezzo_main'),
    path('export/', views.export_excel, name='stesso_prezzo_export'),
]
