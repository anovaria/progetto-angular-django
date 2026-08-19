# modules/entrata_merci/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.entrata_merci_pdv, name='entrata_merci_pdv')
]