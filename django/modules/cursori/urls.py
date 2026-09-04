from django.urls import path
from . import views

app_name = 'cursori'

urlpatterns = [
    path('',                  views.home,            name='home'),
    path('dettaglio/',        views.dettaglio,       name='dettaglio'),
    path('stampa/',           views.stampa,          name='stampa'),
    path('stampa/vedi/',      views.vedi_stampa,     name='vedi_stampa'),
    path('stampa/preview/',   views.stampa_preview,  name='stampa_preview'),
    path('stampa/qta/',       views.stampa_salva_qta, name='stampa_salva_qta'),
    path('stampa/cancella/',  views.stampa_cancella,  name='stampa_cancella'),
    path('stampa/invia/',     views.stampa_invia,     name='stampa_invia'),
    path('stampa/invia-email/', views.stampa_invia_email, name='stampa_invia_email'),
]
