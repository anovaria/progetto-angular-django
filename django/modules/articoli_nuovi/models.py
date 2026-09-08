from django.db import models

class ArticoliNuovi(models.Model):
    cod_articolo = models.CharField(db_column='CODART', max_length=26, null=False, blank=True, primary_key=True)
    descr_articolo = models.CharField(db_column='DESCRART', max_length=8000, null=True, blank=True)
    stato = models.CharField(db_column='STATO', max_length=16, null=True, blank=True)
    giac_pdv = models.FloatField(db_column='GIACENZA_PDV', null=True, blank=True)
    giac_dep = models.FloatField(db_column='GIACENZA_DEPOSITO', null=True, blank=True)
    dta_aggio = models.CharField(db_column='DTAAGGIO', max_length=20, null=True, blank=True)
    ultimo_ordine = models.CharField(db_column='ULTIMO_ORDINE', max_length=20, null=True, blank=True)
    data_consegna = models.CharField(db_column='DATA_CONSEGNA', max_length=20, null=True, blank=True)
    ultima_vendita = models.CharField(db_column='ULTIMA_VENDITA', max_length=20, null=True, blank=True)
    ultimo_ricevimento = models.CharField(db_column='ULTIMO_RICEVIMENTO', max_length=20, null=True, blank=True)
    corsia = models.FloatField(db_column='Corsia', null=True, blank=True)
    campata = models.FloatField(db_column='Campata', null=True, blank=True)
    tipo_art = models.FloatField(db_column='TIPOA', null=True, blank=True)
    tipo_ean = models.DecimalField(db_column='TIPO', max_digits=5, decimal_places=0, null=True, blank=True)
    ean = models.CharField(db_column='EAN', max_length=28, null=True, blank=True)
    eanprinc = models.DecimalField(db_column='EANPRINC', max_digits=5, decimal_places=1, null=True, blank=True)
    settore = models.CharField(db_column='SETTORE', max_length=26, null=True, blank=True)
    buyer = models.CharField(db_column='Buyer',max_length=32, null=True, blank=True)
    reparto = models.CharField(db_column='REPARTO',max_length=26, null=True, blank=True)
    ccom = models.CharField(db_column='CCOM',max_length=16, null=True, blank=True)
    descr_for = models.CharField(db_column='DESCRCCOM', max_length=70, null=True, blank=True)
    facing = models.FloatField(db_column='FACING', null=True, blank=True)
    gest_rio = models.CharField(db_column='GEST', max_length=8000, null=True, blank=True)
    vl = models.CharField(db_column='VL', max_length=6, null=True, blank=True)
    pzxcart = models.FloatField(db_column='PZXCART', null=True, blank=True)
    qta_in_ordine = models.FloatField(db_column='QTA_IN_ORDINE', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'v_masterdata'
        verbose_name = 'ArticoliNuovi (v_masterdata)'

    def __str__(self):
        return f'{self.cod_articolo} - {self.descr_articolo}'