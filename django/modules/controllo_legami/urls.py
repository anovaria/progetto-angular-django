from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='controllo_legami_main'),
    path('export/', views.export_excel, name='controllo_legami_export'),
]
