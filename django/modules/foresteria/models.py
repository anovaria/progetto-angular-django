from django.db import models


class Prenotazione(models.Model):

    class Camera(models.TextChoices):
        MONTE_BIANCO = 'MB', 'Monte Bianco'
        CERVINO = 'CE', 'Cervino'

    camera = models.CharField(max_length=2, choices=Camera.choices)
    nome = models.CharField(max_length=50)
    cognome = models.CharField(max_length=50)
    azienda = models.CharField(max_length=100)
    data_arrivo = models.DateField()
    data_partenza = models.DateField()
    note = models.TextField(max_length=500, blank=True)

    class Meta:
        ordering = ['data_arrivo']
        verbose_name = 'prenotazione'
        verbose_name_plural = 'prenotazioni'

    def __str__(self):
        arrivo = self.data_arrivo.strftime('%d/%m/%Y')
        partenza = self.data_partenza.strftime('%d/%m/%Y')
        return f"{self.get_camera_display()} - {self.cognome} {self.nome} ({arrivo} → {partenza})"