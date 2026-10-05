from django.urls import path
from . import views

app_name = 'foresteria'

urlpatterns = [
    path('', views.planning, name='planning'),
]