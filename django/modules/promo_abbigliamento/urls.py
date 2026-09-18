from django.urls import path
from . import views

app_name = 'promo_abbigliamento'

urlpatterns = [
    path('', views.promo_abbigliamento, name='home'),
    path('testata', views.crea_testata , name='crea'),
    path('<str:codice_promo>/csv', views.scarica_csv_promo , name='csv')
]