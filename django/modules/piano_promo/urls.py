from django.urls import path
from . import views

app_name = 'piano-promo'

urlpatterns = [
    path('',                        views.index,         name='index'),
    path('dati/',                   views.dati_live,     name='dati_live'),
    path('nuova/',                  views.nuova,         name='nuova'),
    path('<int:pk>/',               views.dettaglio,     name='dettaglio'),
    path('<int:pk>/elimina/',       views.elimina,       name='elimina'),
    path('<int:pk>/export/',             views.export_sessione,      name='export'),
    path('<int:pk>/segna-tutti-ordinato/', views.segna_tutti_ordinato, name='segna_tutti_ordinato'),
    path('<int:pk>/aggiungi-articoli/',   views.aggiungi_articoli,    name='aggiungi_articoli'),
    path('<int:pk>/aggiorna-lista/',      views.aggiorna_lista,       name='aggiorna_lista'),
    path('riga/<int:pk>/aggiorna/', views.aggiorna_riga, name='aggiorna_riga'),
    path('riga/<int:pk>/elimina/',  views.elimina_riga,  name='elimina_riga'),
]
