from django.db import models

class MasterdataAll(models.Model):

    id = models.AutoField(primary_key=True, db_column='ID')
    codart = models.CharField(max_length=50, db_column='CODART')
    descrart = models.CharField(max_length=200, db_column='DESCRART')
    codforn = models.CharField(max_length=50, db_column='CODFORN')
    descforn = models.CharField(max_length=200, db_column='DESCFORN')
    ccom = models.CharField(max_length=50, db_column='CCOM')
    descrccom = models.CharField(max_length=200,db_column='DESCRCCOM')
    codartfo = models.CharField(max_length=100, db_column='CODARTFO')
    stato = models.CharField(max_length=5, db_column='STATO')
    iva = models.CharField(max_length=10, db_column='IVA')
    ean = models.CharField(max_length=20, db_column='EAN')
    pracq = models.DecimalField(max_digits=10, decimal_places=2, db_column='PRACQ')
    przvend = models.DecimalField(max_digits=10, decimal_places=2, db_column='PRZ_VEND')

    class Meta:
        managed = False
        db_table = 't_masterdataall'


    def __str__(self):
        return f"{self.codart} - {self.descrart}"

