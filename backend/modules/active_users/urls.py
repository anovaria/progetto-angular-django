"""
Active Users - URLs
Da aggiungere in modules/active_users/urls.py
"""
from django.urls import path
from . import views

app_name = 'active_users'

urlpatterns = [
    # GET /api/active-users/?minutes=5
    path('', views.active_users_api, name='active-users'),
    # GET /api/active-users/history/?hours=24
    path('history/', views.active_users_history_api, name='active-users-history'),
    path('debug/', views.debug_auth, name='debug-auth'),
]
