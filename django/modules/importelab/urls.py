from django.urls import path
from .views import (
    dashboard_view,
    ordine_email_view,
    delete_batch_view,
    sync_gold_view,
    regen_intermediate_view,
    report_r_aggprezziacq_view,
    report_r_aggprezziacq_pdf_view,
    report_r_aggean_view,
    report_r_aggean_pdf_view,
    report_r_agglogistica_view,
    report_r_agglogistica_pdf_view,
)

app_name = 'importelab'

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('batch/<int:pk>/delete/', delete_batch_view, name='delete_batch'),
    path('gold/sync/', sync_gold_view, name='sync_gold'),
    path('intermediate/regen/', regen_intermediate_view, name='regen_intermediate'),
    path('ordine/email/', ordine_email_view, name='ordine_email'),
    path('report/prezziacq/', report_r_aggprezziacq_view, name='report_r_aggprezziacq'),
    path('report/prezziacq/pdf/', report_r_aggprezziacq_pdf_view, name='report_r_aggprezziacq_pdf'),
    path('report/ean/', report_r_aggean_view, name='report_r_aggean'),
    path('report/ean/pdf/', report_r_aggean_pdf_view, name='report_r_aggean_pdf'),
    path('report/logistica/', report_r_agglogistica_view, name='report_r_agglogistica'),
    path('report/logistica/pdf/', report_r_agglogistica_pdf_view, name='report_r_agglogistica_pdf'),
]