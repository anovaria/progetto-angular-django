from django.db import models


class ScansioneOrtofrutta(models.Model):
    ean_scansionato = models.CharField(max_length=20)
    data_competenza = models.DateField(null=True, blank=True)
    codart = models.CharField(max_length=26, blank=True, default='')
    peso_num = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    qta = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    gest = models.CharField(max_length=20, blank=True, default='')
    utente = models.CharField(max_length=50)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'ortofrutta'
        db_table = 'ortofrutta_scansione'


class ListinoGiorno(models.Model):
    data_competenza = models.DateField()
    codart = models.CharField(max_length=26)
    prezzo_listino = models.DecimalField(max_digits=10, decimal_places=4)
    utente_inserimento = models.CharField(max_length=50)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'ortofrutta'
        db_table = 'ortofrutta_listino_giorno'
        constraints = [
            models.UniqueConstraint(
                fields=['data_competenza', 'codart'],
                name='uniq_listino_giorno_articolo'
            )
        ]


class Ean(models.Model):
    """
    dbo.t_t_ean1 - EAN articoli (Db_GoldReport, sola lettura).
    """
    ID = models.IntegerField(primary_key=True, db_column='ID')
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    CODART = models.CharField(max_length=26, blank=True, default='', db_index=True)
    DESCRART = models.CharField(max_length=255, blank=True, default='')
    EAN = models.CharField(max_length=28, blank=True, default='')
    EANA = models.CharField(max_length=38, blank=True, default='')
    TIPO = models.FloatField(default=0)
    PRINC = models.FloatField(default=0)
    STEAN = models.FloatField(default=0)
    DTAINI = models.CharField(max_length=20, blank=True, default='')
    STAFINE = models.CharField(max_length=20, blank=True, default='')
    GEST = models.CharField(max_length=255, blank=True, default='')
    DataCreazione = models.DateTimeField(null=True, blank=True)
    iva = models.FloatField(default=0)

    class Meta:
        managed = False
        db_table = 't_t_ean1'
        app_label = 'ortofrutta'