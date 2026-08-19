from django.db import models

class V_RicevimentiGoldArtFo(models.Model):

    data_aggio =models.CharField(max_length=10,db_column='DTAAGGIO', null=True)
    data=models.CharField(max_length=10,db_column='DATA', null=True)
    settore=models.CharField(max_length=50,db_column='SETTORE', null=True)
    reparto=models.CharField(max_length=50,db_column='REPARTO', null=True)
    cod_interno_ric=models.IntegerField(db_column='CODICE_INTERNO_RIC', primary_key=True)
    cod_ext_ric=models.CharField(max_length=13,db_column='COD_EXT_RIC', null=True)
    fornitore=models.CharField(max_length=4000,db_column='FORNITORE', null=True)
    desc_forn=models.CharField(max_length=4000,db_column='DESC_FORN', null=True)
    contr_comm=models.CharField(max_length=4000,db_column='CONTRATTO_COMMERCIALE', null=True)
    codartfo=models.CharField(max_length=20,db_column='COD_ARTFO', null=True)
    cod_art=models.CharField(max_length=4000,db_column='COD_ARTICOLO', null=True)
    desc_art=models.CharField(max_length=4000,db_column='DESCRIZIONE_ART', null=True)
    stato=models.CharField(max_length=8,db_column='STATO', null=True)
    unita_misura=models.CharField(max_length=12,db_column='UNITA_MISURA', null=True)
    quantita_ordinata = models.DecimalField(max_digits=10, decimal_places=3, db_column='QUANTITA_ORDINATA', null=True)
    peso_ordinato=models.DecimalField(max_digits=10, decimal_places=3, db_column='PESO_ORDINATO', null=True)
    quantita_ricevuta=models.DecimalField(max_digits=9, decimal_places=3, db_column='QUANTITA_RICEVUTA', null=True)
    peso_ricevuto=models.DecimalField(max_digits=9, decimal_places=3, db_column='PESO_RICEVUTO', null=True)
    prezzo_unitario=models.DecimalField(max_digits=15, decimal_places=5, db_column='PREZZO_UNITARIO', null=True)
    tot_ricevuto=models.DecimalField(max_digits=18, decimal_places=5, db_column='TOT_RICEVUTO', null=True)
    corsia = models.FloatField(db_column='CORSIA', null=True)
    campata = models.FloatField(db_column='CAMPATA', null=True)
    facing=models.FloatField(db_column='FACING', null=True)
    pzxcart=models.FloatField(db_column='PZXCART', null=True)
    giacenza_pdv=models.FloatField(db_column='GIACENZA_PDV', null=True)
    sito=models.IntegerField(db_column='SITO', null=True)
    ean=models.CharField(max_length=14,db_column='EAN', null=True)
    eanprinc=models.IntegerField(db_column='EANPRINC', null=True)
    tipo=models.IntegerField(db_column='TIPO', null=True)

    class Meta:
        managed = False
        db_table = 'v_RicevimentiGoldArtFo'

class EntrataMerciOverride(models.Model):
    cod_interno_ric = models.IntegerField()
    cod_art = models.CharField(max_length=4000, default='')
    data_ricevimento_modificata = models.DateField()
    utente = models.CharField(max_length=50, null=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    aggiornato_il = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cod_interno_ric', 'cod_art')

    def __str__(self):
        return f"Override {self.cod_interno_ric}/{self.cod_art} - {self.data_ricevimento_modificata}"