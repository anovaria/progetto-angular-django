"""
Models per app AssoArticoli
Utilizza viste dal database Gold (Db_GoldReport) in modalità read-only
"""
from django.db import models


class MasterAssortimenti(models.Model):
    """
    Vista dbo.v_MasterAssortimenti - Dati master assortimenti articoli
    """
    dtaaggio = models.CharField(db_column='DTAAGGIO', max_length=50, null=True, blank=True)
    sito = models.CharField(db_column='SITO', max_length=50, null=True, blank=True)
    sett = models.CharField(db_column='SETT', max_length=10, null=True, blank=True)
    rep = models.CharField(db_column='REP', max_length=10, null=True, blank=True)
    descrrep = models.CharField(db_column='DESCRREP', max_length=100, null=True, blank=True)
    srep = models.CharField(db_column='SREP', max_length=10, null=True, blank=True)
    descrsrep = models.CharField(db_column='DESCRSREP', max_length=100, null=True, blank=True)
    fam = models.CharField(db_column='FAM', max_length=20, null=True, blank=True)
    descrfam = models.CharField(db_column='DESCRFAM', max_length=100, null=True, blank=True)
    codforn = models.CharField(db_column='CODFORN', max_length=20, null=True, blank=True)
    descforn = models.CharField(db_column='DESCFORN', max_length=100, null=True, blank=True)
    ccom = models.CharField(db_column='CCOM', max_length=50, null=True, blank=True)
    descrccom = models.CharField(db_column='DESCRCCOM', max_length=100, null=True, blank=True)
    linea_prodotto = models.CharField(db_column='LINEA_PRODOTTO', max_length=20, null=True, blank=True)
    descr_linea = models.CharField(db_column='DESCR_LINEA', max_length=100, null=True, blank=True)
    tipo_riordino = models.CharField(db_column='TIPO_RIORDINO', max_length=20, null=True, blank=True)
    codartfo = models.CharField(db_column='CODARTFO', max_length=20, null=True, blank=True)
    codart = models.CharField(db_column='CODART', max_length=20, primary_key=True)
    stato = models.CharField(db_column='STATO', max_length=10, null=True, blank=True)
    descrart = models.CharField(db_column='DESCRART', max_length=200, null=True, blank=True)
    pracq = models.DecimalField(db_column='PRACQ', max_digits=15, decimal_places=2, null=True, blank=True)
    iva = models.DecimalField(db_column='IVA', max_digits=5, decimal_places=2, null=True, blank=True)
    tipoean = models.IntegerField(db_column='TIPOEAN', null=True, blank=True)
    ean = models.CharField(db_column='EAN', max_length=50, null=True, blank=True)
    eana = models.CharField(db_column='EANA', max_length=50, null=True, blank=True)
    codartexpo = models.CharField(db_column='CODARTEXPO', max_length=20, null=True, blank=True)
    descrizioneexpo = models.CharField(db_column='DESCRIZIONEEXPO', max_length=200, null=True, blank=True)
    statoe = models.CharField(db_column='STATOE', max_length=10, null=True, blank=True)
    contiene = models.IntegerField(db_column='CONTIENE', null=True, blank=True)
    itf14 = models.CharField(db_column='ITF14', max_length=50, null=True, blank=True)
    eanexpo = models.CharField(db_column='Expr1', max_length=50, null=True, blank=True)
    fornprinc = models.IntegerField(db_column='FORNPRINC', null=True, blank=True)
    tcol = models.CharField(db_column='TCOL', max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'v_MasterAssortimenti'
        app_label = 'asso_articoli'
        ordering = ['sett', 'rep', 'srep', 'fam', 'ccom', 'linea_prodotto']

    def __str__(self):
        return f"{self.codart} - {self.descrart}"


class AllArticolo(models.Model):
    """
    Vista dbo.v_AllArticolo - Giacenze e dati articoli
    """
    eanprinc = models.IntegerField(db_column='EANPRINC', null=True, blank=True)
    ean = models.CharField(db_column='EAN', max_length=20, null=True, blank=True)
    stato = models.CharField(db_column='STATO', max_length=10, null=True, blank=True)
    prezzovend = models.DecimalField(db_column='PREZZOVEND', max_digits=15, decimal_places=2, null=True, blank=True)
    giacenza_pdv = models.DecimalField(db_column='GIACENZA_PDV', max_digits=15, decimal_places=2, null=True, blank=True)
    giacenza_deposito = models.DecimalField(db_column='GIACENZA_DEPOSITO', max_digits=15, decimal_places=2, null=True, blank=True)
    codart = models.CharField(db_column='CODART', max_length=20, primary_key=True)

    class Meta:
        managed = False
        db_table = 'v_AllArticolo'
        app_label = 'asso_articoli'

    def __str__(self):
        return f"{self.codart} - EAN: {self.ean}"
