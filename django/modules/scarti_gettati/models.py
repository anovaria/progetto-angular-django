from django.db import models


class EanArticolo(models.Model):
    """
    Tabella t_t_Ean nel DB goldreport — sola lettura.
    Lookup: EAN__startswith con i primi 8 char dell'EAN scansionato + PRINC=1.
    """
    ean = models.CharField(db_column='EAN', max_length=14, primary_key=True)
    codart = models.CharField(db_column='CODART', max_length=13, null=True, blank=True)
    descrart = models.CharField(db_column='DESCRART', max_length=4000, null=True, blank=True)
    tipo = models.IntegerField(db_column='TIPO', null=True, blank=True)
    princ = models.IntegerField(db_column='PRINC', null=True, blank=True)
    stean = models.IntegerField(db_column='STEAN', null=True, blank=True)
    gest = models.CharField(db_column='GEST', max_length=4000, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_t_Ean'
        app_label = 'scarti_gettati'

    def __str__(self):
        return f"{self.codart} - {self.descrart}"


class ScartoGiornaliero(models.Model):
    """
    Scarti e gettato banco taglio — causale 12.
    Salvati su DjangoIntranet (DB default).
    """
    data = models.DateField()
    codice_ean_letto = models.CharField(max_length=30)
    codart = models.IntegerField()
    descrart = models.CharField(max_length=200)
    ean_principale = models.BigIntegerField()
    peso_kg = models.DecimalField(max_digits=8, decimal_places=3)
    utente = models.CharField(max_length=50)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'scarti_gettati_scarto'
        ordering = ['-creato_il']

    def __str__(self):
        return f"{self.data} - {self.codart} - {self.peso_kg} kg"
