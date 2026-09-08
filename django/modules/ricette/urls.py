from django.urls import path
from . import views

app_name = 'ricette'

urlpatterns = [
    path('',                        views.ricette_list,        name='list'),
    path('nuova/',                  views.ricetta_create,      name='create'),
    path('<int:pk>/',               views.ricetta_detail,      name='detail'),
    path('<int:pk>/modifica/',      views.ricetta_edit,        name='edit'),
    path('<int:pk>/elimina/',       views.ricetta_delete,      name='delete'),
    path('api/articoli/',           views.api_search_articoli, name='api_articoli'),
]
