from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='art_no_ean_main'),
    path('export/', views.export_excel, name='art_no_ean_export'),
]
