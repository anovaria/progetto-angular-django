from django.urls import path
from . import views

app_name = 'masterdatacategory'

urlpatterns = [
    path('', views.masterdatacategory_list, name='list'),
    path('export/', views.masterdatacategory_export, name='export'),
]
