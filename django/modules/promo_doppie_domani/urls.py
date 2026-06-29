from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='promo_doppie_domani_main'),
    path('export/', views.export_excel, name='promo_doppie_domani_export'),
]
