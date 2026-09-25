from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='ins_mass_attributi_abbig'),
    path('download/', views.download, name='ins_mass_attributi_abbig_download'),
]
