from django.urls import path

from . import views

app_name = 'rotazione-minmax'

urlpatterns = [
    path('', views.index, name='index'),
    path('dati/', views.dati, name='dati'),
]

