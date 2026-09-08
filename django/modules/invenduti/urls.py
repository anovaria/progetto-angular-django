from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='invenduti_main'),
    path('anteprima/<str:opzione>/', views.anteprima, name='invenduti_anteprima'),
    path('export/<str:opzione>/', views.export_excel, name='invenduti_export'),
]