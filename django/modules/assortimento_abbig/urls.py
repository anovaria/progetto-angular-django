from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='assortimento_abbig_main'),
    path('api/fornitori/', views.api_fornitori, name='assortimento_abbig_fornitori'),
    path('api/ccom/', views.api_ccom, name='assortimento_abbig_ccom'),
    path('api/attributi/', views.api_attributi, name='assortimento_abbig_attributi'),
    path('stampa/', views.stampa, name='assortimento_abbig_stampa'),
    path('export/', views.export_excel, name='assortimento_abbig_export'),
]
