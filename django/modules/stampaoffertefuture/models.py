from django.db import models


class ArtPromoFuture(models.Model):
    """Mappa la view v_ArtPromoFuture su Db_GoldReport."""
    settore = models.IntegerField(db_column='SETTORE', null=True)
    reparto = models.IntegerField(db_column='REPARTO', null=True)
    descrep = models.CharField(max_length=100, db_column='DESCREP', null=True)
    sottoreparto = models.IntegerField(db_column='SOTTOREPARTO', null=True)
    descsrep = models.CharField(max_length=100, db_column='DESCSREP', null=True)
    codforn = models.IntegerField(db_column='CODFORN', null=True)
    descforn = models.CharField(max_length=100, db_column='DESCFORN', null=True)
    oplcexopr = models.CharField(max_length=20, db_column='OPLCEXOPR', null=True)   # codice piano promo
    dtaini = models.DateField(db_column='DTAINI', null=True)
    dtafine = models.DateField(db_column='DTAFINE', null=True)
    arvcexr = models.CharField(max_length=20, db_column='ARVCEXR', null=True)       # codart
    arccode = models.CharField(max_length=20, db_column='ARCCODE', null=True)
    prz_off = models.DecimalField(max_digits=10, decimal_places=5, db_column='PRZ_OFF', null=True)
    giacenza_pdv = models.DecimalField(max_digits=18, decimal_places=3, db_column='GIACENZA_PDV', null=True)
    qta_in_ordine = models.DecimalField(max_digits=18, decimal_places=3, db_column='QTA_IN_ORDINE', null=True)
    ultimo_ordine = models.DateField(db_column='ULTIMO_ORDINE', null=True)
    ccom = models.CharField(max_length=20, db_column='CCOM', null=True)
    descrccom = models.CharField(max_length=100, db_column='DESCRCCOM', null=True)
    eanprinc = models.IntegerField(db_column='EANPRINC', null=True)
    stato = models.CharField(max_length=5, db_column='STATO', null=True)
    prz_std = models.DecimalField(max_digits=10, decimal_places=5, db_column='prz_std', null=True)
    famiglia = models.IntegerField(db_column='FAMIGLIA', null=True)
    descfam = models.CharField(max_length=100, db_column='DESCFAM', null=True)
    codartfo = models.CharField(max_length=30, db_column='CODARTFO', null=True)
    buyer = models.CharField(max_length=100, db_column='BUYER', null=True)
    codpiano = models.CharField(max_length=20, db_column='CODPIANO', null=True)
    gest = models.CharField(max_length=20, db_column='GEST', null=True)
    giacenza_deposito = models.DecimalField(max_digits=18, decimal_places=3, db_column='GIACENZA_DEPOSITO', null=True)
    vl = models.CharField(max_length=10, db_column='VL', null=True)
    indpick = models.CharField(max_length=20, db_column='INDPICK', null=True)
    cartpall = models.IntegerField(db_column='CARTPALL', null=True)
    pzxcart = models.IntegerField(db_column='PZXCART', null=True)
    dtaaggio = models.DateField(db_column='DTAAGGIO', null=True)
    description = models.CharField(max_length=200, db_column='DESCRIPTION', null=True)
    descrizione = models.CharField(max_length=200, db_column='Descrizione', null=True)

    class Meta:
        managed = False
        db_table = 'v_ArtPromoFuture'
        app_label = 'stampaoffertefuture'


class AllArticolo(models.Model):
    """Mappa la view v_AllArticolo su Db_GoldReport."""
    codart = models.CharField(max_length=20, db_column='CODART', null=True)
    eanprinc = models.IntegerField(db_column='EANPRINC', null=True)
    ean = models.CharField(max_length=20, db_column='EAN', null=True)
    stato = models.CharField(max_length=5, db_column='STATO', null=True)
    prezzovend = models.DecimalField(max_digits=10, decimal_places=5, db_column='PREZZOVEND', null=True)

    class Meta:
        managed = False
        db_table = 'v_AllArticolo'
        app_label = 'stampaoffertefuture'
