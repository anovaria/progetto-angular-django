from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='scarti_gettati_index'),
    path('api/lookup-ean/', views.api_lookup_ean, name='scarti_gettati_lookup_ean'),
    path('salva/', views.salva_scarto, name='scarti_gettati_salva'),
    path('elimina/<int:pk>/', views.elimina_scarto, name='scarti_gettati_elimina'),
    path('riepilogo/', views.riepilogo, name='scarti_gettati_riepilogo'),
    path('export/', views.export_riepilogo, name='scarti_gettati_export'),
]
