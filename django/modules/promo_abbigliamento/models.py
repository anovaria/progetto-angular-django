from django.db import models

class PromoStorico(models.Model):
    """Storico da NUMERO_PROMO_2-base.xlsx — caricato una tantum, sola lettura."""
    tipo_promo = models.CharField(max_length=1, default='M')
    codice_promo = models.CharField(max_length=10)
    descrizione = models.CharField(max_length=100)
    data_inizio_sellout = models.DateField(null=True, blank=True)
    data_fine_sellout = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'promo_storico'
        managed = False
        ordering = ['-codice_promo']

    def __str__(self):
        return f'{self.codice_promo} - {self.descrizione}'


class PromoTestata(models.Model):
    """Nuove promo create via form — scrivibile."""
    tipo_promo = models.CharField(max_length=1, default='M')
    codice_promo = models.CharField(max_length=10, unique=True)
    descrizione = models.CharField(max_length=50)
    data_inizio_sellout = models.DateField()
    data_fine_sellout = models.DateField()
    creato_da = models.CharField(max_length=50)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promo_testata'
        managed = False
        ordering = ['-creato_il']

    def __str__(self):
        return f'{self.codice_promo} - {self.descrizione}'
