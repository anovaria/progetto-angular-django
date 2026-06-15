"""
Active Users - URLs
Da aggiungere in modules/active_users/urls.py
"""
from django.urls import path
from . import views

app_name = 'active_users'

urlpatterns = [
    path('', views.active_users_api, name='active-users'),
    path('history/', views.active_users_history_api, name='active-users-history'),
    path('debug/', views.debug_auth, name='debug-auth'),
]

# URL pagina (montata su /app/active-users/)
page_urlpatterns = [
    path('', views.active_users_page, name='page'),
]
