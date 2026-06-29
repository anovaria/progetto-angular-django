from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='prezzo_promo_alto_main'),
    path('export/', views.export_excel, name='prezzo_promo_alto_export'),
]
