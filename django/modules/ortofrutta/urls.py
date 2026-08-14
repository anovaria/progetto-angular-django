from django.urls import path
from . import views

app_name = 'ortofrutta'

urlpatterns = [
    path('', views.scansione, name='scansione'),
    path('salva/', views.scansione_salva, name='scansione_salva'),
    path('elimina/<int:pk>/', views.scansione_elimina, name='scansione_elimina'),
    path('modifica-pesoqta/<int:pk>/', views.scansione_modifica_pesoqta,name='scansione_modifica_pesoqta'),
    path('modifica-data/<int:pk>/', views.scansione_modifica_data, name='scansione_modifica_data'),
    path('listino/', views.listino, name='listino'),
    path('listino-salva/', views.listino_salva, name='listino_salva'),
    path('report/', views.report, name='report'),
    path('report-pdf/',views.report_pdf, name='report_pdf')
]
