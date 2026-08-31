from django.db import models

class VLuke(models.Model):
    dta_aggio = models.CharField(db_column='DTAAGGIO', max_length=10, null=True, blank=True)
    settore = models.CharField(db_column='SETTORE', max_length=13, null=True, blank=True)
    descr_settore = models.CharField(db_column='DESCRSETTORE', max_length=50, null=True, blank=True)
    reparto = models.CharField(db_column='REP', max_length=13, null=True, blank=True)
    descr_reparto = models.CharField(db_column='DESCRREP', max_length=50, null=True, blank=True)
    cod_articolo = models.CharField(db_column='CODARTICOLO', max_length=13, primary_key=True)
    descr_articolo = models.CharField(db_column='DESCRART', max_length=4000, null=True, blank=True)
    stato = models.CharField(db_column='STATO', max_length=8)
    giac_pdv = models.FloatField(db_column='GIAC_PDV', null=True, blank=True)
    ultima_vendita = models.DateTimeField(db_column='ULTIMA_VENDITA', null=True, blank=True)
    giac_dep = models.FloatField(db_column='GIAC_DEP', null=True, blank=True)
    corsia = models.CharField(db_column='Corsia', max_length=10, null=True, blank=True)
    campata = models.CharField(db_column='Campata', max_length=10, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'v_luke'
        verbose_name = 'Giacenza (v_luke)'
        verbose_name_plural = 'Giacenze (v_luke)'

    def __str__(self):
        return f'{self.cod_articolo} - {self.descr_articolo}'
