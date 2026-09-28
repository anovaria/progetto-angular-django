from django.db import models


class RotazForn3(models.Model):
    codarticolo = models.CharField(primary_key=True, max_length=13)
    sito = models.DecimalField(max_digits=5, decimal_places=0, db_column='SITO')
    sett = models.CharField(max_length=13, db_column='SETT')
    rep = models.CharField(max_length=13, db_column='REP')
    srep = models.CharField(max_length=13, db_column='SREP')
    fam = models.CharField(max_length=13, db_column='FAM')
    descrfam = models.CharField(max_length=50, db_column='DESCRFAM')
    foprinc = models.DecimalField(max_digits=1, decimal_places=0, db_column='FOPRINC')
    ordinabile = models.CharField(max_length=3, db_column='Ordinabile')
    codforn = models.CharField(max_length=4000, db_column='CODFORN')
    ccom = models.CharField(max_length=4000, db_column='CCOM')
    descrccom = models.CharField(max_length=4000, db_column='DESCRCCOM')
    descr_linea = models.CharField(max_length=4000, db_column='DESCR_LINEA')
    corsia = models.CharField(max_length=10, db_column='Corsia', null=True)
    campata = models.CharField(max_length=10, db_column='Campata', null=True)
    facing = models.CharField(max_length=10, null=True)
    min_qta = models.CharField(max_length=10, db_column='Min', null=True)
    max_qta = models.CharField(max_length=10, db_column='Max', null=True)
    qtamax = models.FloatField(null=True)
    rotanooff = models.FloatField(db_column='ROTANOOFF', null=True)
    rotaoff = models.FloatField(db_column='ROTAOFF', null=True)
    pzxcart = models.FloatField(db_column='PZXCART', null=True)
    descrart = models.CharField(max_length=4000, db_column='DESCRART')
    ean = models.CharField(max_length=14, db_column='EAN')
    stato = models.CharField(max_length=8, db_column='STATO', null=True)
    pick = models.CharField(max_length=15, null=True)
    baricentro = models.CharField(max_length=15, db_column='BARICENTRO', null=True)
    dtaaggio = models.CharField(max_length=10, db_column='DTAAGGIO', null=True)
    giacenza_pdv = models.FloatField(db_column='GIACENZA_PDV', null=True)
    giacenza_deposito = models.FloatField(db_column='GIACENZA_DEPOSITO', null=True)

    class Meta:
        managed = False
        db_table = 'v_RotazForn3'
