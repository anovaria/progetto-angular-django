from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('utenti-online/', views.utenti_online_view, name='utenti_online'),
    path('admin-msg/', views.admin_msg_view, name='admin_msg'),
    path('admin-permessi/', views.admin_permessi_view, name='admin_permessi'),
    path('kick-user/', views.kick_user_view, name='kick_user'),
]