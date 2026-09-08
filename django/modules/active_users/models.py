"""
Active Users - Models
Tracciamento utenti attivi sul portale in tempo reale.
Da aggiungere in modules/active_users/models.py
"""
from django.db import models


class UserActivity(models.Model):
    """
    Traccia l'ultima attività di ogni utente sul portale.
    Un record per utente, aggiornato ad ogni richiesta.
    """
    username = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Username"
    )
    display_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Nome visualizzato"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name="Ultima attività"
    )
    last_path = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Ultima pagina visitata"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Indirizzo IP"
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="User Agent"
    )
    environment = models.CharField(
        max_length=10,
        default='dev',
        db_index=True,
        verbose_name="Ambiente"
    )

    class Meta:
        db_table = 'user_activity'
        managed = False
        verbose_name = "Attività utente"
        verbose_name_plural = "Attività utenti"
        ordering = ['-last_activity']
        unique_together = [['username', 'environment']]

    def __str__(self):
        return f"{self.username} - {self.last_activity}"
