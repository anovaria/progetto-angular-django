from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='art_stato_ord_aperta_main'),
    path('export/', views.export_excel, name='art_stato_ord_aperta_export'),
]
