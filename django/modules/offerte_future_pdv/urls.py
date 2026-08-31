from django.urls import path
from . import views

app_name = 'offerte-future-pdv'

urlpatterns = [
    path('', views.index, name='index'),
    path('anteprima/', views.anteprima, name='anteprima'),
    path('export/', views.export_excel, name='export_excel'),
    path('pdf/', views.report_pdf, name='report_pdf'),
    path('fornitori/', views.fornitori_per_piano, name='fornitori_per_piano'),
]
