from django.apps import AppConfig

class ModulesAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.auth'    # percorso Python
    label = 'modules_auth'  # label univoca per Django
