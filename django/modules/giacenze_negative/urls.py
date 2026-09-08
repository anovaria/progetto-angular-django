from django.urls import path
from . import views

app_name = 'giacenze-negative'

urlpatterns = [
    path('', views.main, name='main'),
]