from django.db import models

class VMasterData(models.Model):

    CODART = models.CharField(max_length=13, primary_key=True)
    CCOM = models.CharField(max_length=8,null=True)
    DESCRCCOM = models.CharField(max_length=35,null=True)
    EAN = models.CharField(max_length=14,null=True)
    CODARTFO = models.CharField(max_length=20,null=True)
    DESCRART = models.CharField(max_length=4000,null=True)
    PRZ_VEND = models.FloatField(null=True)

    class Meta:
        managed = False
        db_table = 'v_masterdata'

