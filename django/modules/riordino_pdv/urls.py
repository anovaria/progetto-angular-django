from django.urls import path
from . import views

app_name = 'riordino_pdv'

urlpatterns = [
    path('', views.parametri_rio, name='parametri_rio'),
    path('avvia/', views.avvia_htmx, name='avvia'),
    path('stato/', views.stato_htmx, name='stato'),
]
