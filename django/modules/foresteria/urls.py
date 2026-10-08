from django.urls import path
from . import views

app_name = 'foresteria'

urlpatterns = [
    path('', views.planning, name='planning'),
    path('prenotazione/', views.nuova_prenotazione, name='prenotazione'),
    path('prenotazione/<int:pk>/', views.modifica_prenotazione, name='modifica'),
    path('prenotazione/<int:pk>/cancella/', views.cancella_prenotazione, name='cancella'),
]