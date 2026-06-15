from django.urls import path
from . import views

app_name = 'rio_fornitori_new'

urlpatterns = [
    path('', views.home, name='home'),
    path('ordine/', views.ordine, name='ordine'),
    path('esegui/', views.esegui, name='esegui'),
    path('modifica-email/', views.modifica_email, name='modifica_email'),
]
