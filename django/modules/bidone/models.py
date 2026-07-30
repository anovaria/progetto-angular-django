from django.db import models


class BidoneAnnotazione(models.Model):
    app_name      = models.CharField(max_length=50)
    record_key    = models.CharField(max_length=300)
    gestito       = models.BooleanField(default=False)
    nota          = models.TextField(blank=True)
    utente        = models.CharField(max_length=100)
    aggiornato_il = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('app_name', 'record_key')
        db_table = 'bidone_annotazione'

    def __str__(self):
        return f"{self.app_name}:{self.record_key} ({'gestito' if self.gestito else 'aperto'})"
