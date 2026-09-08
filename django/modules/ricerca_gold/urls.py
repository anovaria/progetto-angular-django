from django.urls import path
from . import views

urlpatterns = [
    path('', views.ricerca, name='ricerca_gold_main'),
    path('export/', views.export_excel, name='ricerca_gold_export'),
]