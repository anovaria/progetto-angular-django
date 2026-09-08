from django.urls import path
from . import views

app_name = 'stampaoffertefuture'

urlpatterns = [
    path('', views.index, name='index'),
    path('anteprima/', views.anteprima, name='anteprima'),
    path('export/', views.export_excel, name='export_excel'),
]
