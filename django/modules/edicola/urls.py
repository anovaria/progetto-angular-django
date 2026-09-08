from django.urls import path

from . import views

app_name = "edicola"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("articoli/", views.articoli_list, name="articoli_list"),
    path("refresh/", views.refresh, name="refresh"),
    path("clear-dates/", views.clear_dates, name="clear_dates"),
    path("save-edits/", views.save_edits, name="save_edits"),
    path("autosave-note/", views.autosave_note, name="autosave_note"),
    path("log/", views.log_list, name="log_list"),
]
