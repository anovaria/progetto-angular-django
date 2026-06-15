from django.urls import path
from . import views

app_name = 'active_users'

urlpatterns = [
    path('', views.active_users_page, name='page'),
]
