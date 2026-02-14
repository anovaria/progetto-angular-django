from django.apps import AppConfig


class ActiveUsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.active_users'
    verbose_name = 'Utenti Attivi'
