from django.urls import path
from . import views 
urlpatterns = [
    path('', views.preventivi, name='preventivi')
]