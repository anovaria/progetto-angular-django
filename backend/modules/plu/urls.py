# modules/plu/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RepartoPlUViewSet

# Router per API REST
router = DefaultRouter()
router.register(r'plu', RepartoPlUViewSet, basename='plu')

urlpatterns = [
    path('', include(router.urls)),
]