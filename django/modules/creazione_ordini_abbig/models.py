from django.core.validators import MinValueValidator
from django.db import models

class Ordine(models.Model):
    codice_ordine = models.CharField(max_length=13)
    numero_riga = models.PositiveIntegerField(default=1)
    codice_fornitore = models.CharField(max_length=10)
    codice_commerciale = models.CharField(max_length=8)
    codice_articolo = models.CharField(max_length=13)
    quantita_ordine = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    codice_filiera = models.PositiveSmallIntegerField(default=1)
    variante_logistica = models.PositiveSmallIntegerField(default=1)
    sito = models.PositiveIntegerField(default=10001)
    data_ordine = models.DateField()
    data_consegna = models.DateField()
    unita_ordine = models.PositiveSmallIntegerField(default=1)
    prezzo_unitario = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    iva_acquisto = models.CharField(max_length=3, null=True, blank=True)
    valuta = models.PositiveSmallIntegerField(default=978)
    stato = models.PositiveSmallIntegerField(default=5)
    creato_da = models.CharField(max_length=100)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ordini_abbig'