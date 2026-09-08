from django.urls import path
from . import views

app_name = 'articoli_nuovi'

urlpatterns = [
    path('', views.lista_articoli_nuovi, name='lista'),
]