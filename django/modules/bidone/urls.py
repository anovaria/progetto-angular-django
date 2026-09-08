from django.urls import path
from . import views

app_name = 'bidone'

urlpatterns = [
    path('annota/', views.annota, name='annota'),
]
