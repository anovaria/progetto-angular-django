# modules/auth/models.py
from django.db import models


class UserAppPermission(models.Model):
    """
    Permessi utente per singola app.
    Gestisce chi può vedere quale app nel portale.
    """
    username = models.CharField(max_length=100, db_index=True)
    app_name = models.CharField(max_length=50)  # 'importelab', 'plu', 'dashboard', 'rossetto'
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_app_permissions'
        unique_together = ['username', 'app_name']
        verbose_name = 'Permesso App Utente'
        verbose_name_plural = 'Permessi App Utenti'
        ordering = ['username', 'app_name']
    
    def __str__(self):
        return f"{self.username} -> {self.app_name}"