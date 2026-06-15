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
    path('lista/',            views.lista,            name='lista'),
    path('lista/cancella/',   views.lista_cancella,   name='lista_cancella'),
    path('lista/chiudi/',     views.lista_chiudi,     name='lista_chiudi'),
    path('posizione/',        views.pos_articoli,     name='pos_articoli'),
    path('posizione/vedi/',   views.vedi_pos_articoli, name='vedi_pos_articoli'),
]
