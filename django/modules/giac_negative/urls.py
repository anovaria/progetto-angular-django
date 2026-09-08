from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='giac_negative_main'),
    path('export/', views.export_excel, name='giac_negative_export'),
]
