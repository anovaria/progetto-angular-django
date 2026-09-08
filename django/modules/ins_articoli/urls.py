from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='ins_art_main'),
    path('download/', views.download, name='ins_art_download'),
]
