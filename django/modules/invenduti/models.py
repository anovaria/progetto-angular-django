from django.db import models


class InvendutiTot(models.Model):
    Dtaaggio = models.DateTimeField(null=True, blank=True)
    dtacreaz = models.DateTimeField(null=True, blank=True)
    Cor = models.CharField(max_length=4, null=True, blank=True)
    Camp = models.CharField(max_length=4, null=True, blank=True)
    s = models.CharField(max_length=13, null=True, blank=True)
    rep = models.CharField(max_length=13, null=True, blank=True)
    Srep = models.CharField(max_length=13, null=True, blank=True)
    Fam = models.CharField(max_length=13, null=True, blank=True)
    StArt = models.CharField(max_length=16, null=True, blank=True)
    CodArticolo = models.CharField(max_length=13, primary_key=True)
    Descrizione_Articolo = models.TextField(null=True, blank=True)
    St = models.CharField(max_length=8, null=True, blank=True)
    Ul_Vend = models.DateTimeField(null=True, blank=True)
    G_PDV = models.FloatField(null=True, blank=True)
    G_Dep = models.FloatField(null=True, blank=True)
    Ul_Ric = models.DateTimeField(null=True, blank=True)
    Ul_Inve = models.DateTimeField(null=True, blank=True)
    Gestione = models.CharField(max_length=3, null=True, blank=True)
    CCOM = models.TextField(null=True, blank=True)
    DESCRCCOM = models.TextField(null=True, blank=True)
    codBuyer = models.CharField(max_length=13, null=True, blank=True)
    buyer = models.CharField(max_length=16, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_invendutiTot'


class MasterData(models.Model):
    CODART = models.CharField(max_length=13, primary_key=True)
    CCOM = models.TextField(null=True, blank=True)
    DESCRCCOM = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_masterData'