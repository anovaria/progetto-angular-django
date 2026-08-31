from django.urls import path
from . import views

app_name = 'plu-web'

urlpatterns = [
    path('', views.plu_list, name='list'),
    path('export/', views.plu_export, name='export'),
    path('stampa/', views.plu_stampa, name='stampa'),
]