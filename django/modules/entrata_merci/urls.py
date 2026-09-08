from django.urls import path
from . import views
from django.views.generic import RedirectView

app_name = 'entrata-merci'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='entrata-merci:magazzino', permanent=False), name='home'),
    path('pdv/', views.entrata_merci_pdv, name='pdv'),
    path('magazzino/', views.entrata_merci_magazzino, name='magazzino'),
    path('modifica-data/<int:pk>/', views.modifica_data, name='modifica_data'),
    path('report-pdf/pdv/', views.report_pdf_pdv, name='report_pdf_pdv'),
    path('report-pdf/magazzino/', views.report_pdf_magazzino, name='report_pdf_magazzino'),
]