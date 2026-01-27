# modules/plu/apps.py
from django.apps import AppConfig


class PluConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.plu'
    verbose_name = 'Gestione PLU'
    
    def ready(self):
        """
        Eseguito quando l'app è pronta
        """
        # Import signals se necessario
        pass
