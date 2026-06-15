from django.urls import path
from . import views

app_name = 'masterdata'

urlpatterns = [
    path('', views.masterdata_list, name='list'),
    path('export/', views.masterdata_export, name='export'),
]
