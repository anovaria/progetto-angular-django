"""
Scarico Promo Reparto - Models
Tabelle locali reparto (schema scaricopromo) + riferimenti a tabelle condivise.
"""
from django.db import models

# Tabelle condivise con CED (importate da scaricopromo)
from modules.scaricopromo.models import (
    PerExport, PerExportStorico,
    VartPromoFuture, VallArticolo, MasterData,
    PianoPromo, RecuperaPromo, Reparti, Ean,
    Noscorep, ArtFrePromo, Attrib1,
)


class ArtFreFase1(models.Model):
    SOBCEXT = models.CharField('Reparto', max_length=26, blank=True, default='')
    TSOBDESC = models.CharField('Desc Reparto', max_length=100, blank=True, default='')
    CNUM = models.CharField('Cod Fornitore', max_length=255, blank=True, default='')
    CNUF = models.CharField('CCOM', max_length=255, blank=True, default='')
    DESC_CNUF = models.CharField('Desc CCOM', max_length=255, blank=True, default='')
    ARTFO = models.CharField('Cod Art Fornitore', max_length=40, blank=True, default='')
    CEXR = models.CharField('Cod Articolo', max_length=26, blank=True, default='', db_index=True)
    DESC_CEXR = models.CharField('Descrizione', max_length=255, blank=True, default='')
    PrezzoVOff = models.CharField('Prezzo Offerta', max_length=50, blank=True, default='')
    VL = models.CharField('Variante Logistica', max_length=10, blank=True, default='')
    TIPO_RIORDINO = models.CharField('Tipo Riordino', max_length=255, blank=True, default='')
    LINEA_PRODOTTO = models.CharField('Linea Prodotto', max_length=255, blank=True, default='')
    Desc_Linea = models.CharField('Desc Linea', max_length=255, blank=True, default='')
    PrezzoV = models.CharField('Prezzo Vendita', max_length=50, blank=True, default='')
    STATO = models.CharField('Stato', max_length=16, blank=True, default='')
    scelta = models.BooleanField('Selezionato', default=False)
    ok = models.CharField(max_length=10, blank=True, default='')
    SOBCINT = models.CharField(max_length=26, blank=True, default='')
    utente = models.CharField('Utente', max_length=100, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.artfrefase1'
        verbose_name = 'Articolo Fase 1'
        verbose_name_plural = 'Articoli Fase 1'

    def __str__(self):
        return f"{self.CEXR} - {self.DESC_CEXR}"


class ArtDaVerificare(models.Model):
    Promozioni = models.CharField(max_length=255, blank=True, default='')
    FornitoreAmministrativo = models.CharField(max_length=255, blank=True, default='')
    ContrattoCommerciale = models.CharField(max_length=255, blank=True, default='')
    RagioneSociale = models.CharField(max_length=255, blank=True, default='')
    CodiceProdotto = models.CharField(max_length=50, blank=True, default='')
    DescrizioneProdotto = models.CharField(max_length=255, blank=True, default='')
    SelezionePromozione = models.CharField(max_length=255, blank=True, default='')
    DataInizio = models.CharField(max_length=50, blank=True, default='')
    DataFine = models.CharField(max_length=50, blank=True, default='')
    DataInizioSellin = models.CharField(max_length=50, blank=True, default='')
    DataFineSellin = models.CharField(max_length=50, blank=True, default='')
    ScontoExtra = models.CharField(max_length=50, blank=True, default='')
    TipoSconto1 = models.CharField(max_length=50, blank=True, default='')
    TipoSconto = models.CharField(max_length=50, blank=True, default='')
    Meccanica = models.CharField(max_length=50, blank=True, default='')
    Meccanicav = models.CharField(max_length=255, blank=True, default='')
    Valore = models.CharField(max_length=50, blank=True, default='')
    Valore1 = models.CharField(max_length=50, blank=True, default='')
    export = models.CharField(max_length=50, blank=True, default='')
    QtaOmaggio = models.CharField(max_length=50, blank=True, default='')
    VL = models.CharField(max_length=50, blank=True, default='')
    promor = models.CharField(max_length=100, blank=True, default='')
    utente = models.CharField('Utente', max_length=100, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.artdaverificare'
        verbose_name = 'Articolo da Verificare'
        verbose_name_plural = 'Articoli da Verificare'

    def __str__(self):
        return f"{self.CodiceProdotto} - {self.DescrizioneProdotto}"


class CodArtPromo(models.Model):
    CodArt = models.CharField(max_length=50, blank=True, default='')
    stato = models.CharField(max_length=10, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.codartpromo'
        verbose_name = 'Cod Art Promo'
        verbose_name_plural = 'Cod Art Promo'

    def __str__(self):
        return self.CodArt


class ImportaArticoliPromo(models.Model):
    REP = models.CharField(max_length=26, blank=True, default='')
    CODFORN = models.CharField(max_length=255, blank=True, default='')
    CCOM = models.CharField(max_length=255, blank=True, default='')
    DESCRCCOM = models.CharField(max_length=255, blank=True, default='')
    CODARTFO = models.CharField(max_length=40, blank=True, default='')
    CODART = models.CharField(max_length=26, blank=True, default='', db_index=True)
    DESCRART = models.CharField(max_length=255, blank=True, default='')
    S = models.CharField(max_length=16, blank=True, default='')
    TCOL = models.CharField(max_length=176, blank=True, default='')
    PRZ_VEND = models.FloatField(default=0)
    PVOF_ARR = models.FloatField('Prezzo Offerta', default=0, db_column='PVOF_ARR')

    class Meta:
        managed = False
        db_table = 'scaricopromo.importaarticolipromo'
        verbose_name = 'Importa Articoli Promo'
        verbose_name_plural = 'Importa Articoli Promo'

    def __str__(self):
        return f"{self.CODART} - {self.DESCRART}"


class Meccanica(models.Model):
    codice = models.CharField(max_length=50, blank=True, default='')
    descrizione = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.meccanica'
        verbose_name = 'Meccanica'
        verbose_name_plural = 'Meccaniche'

    def __str__(self):
        return f"{self.codice} - {self.descrizione}"


class TipoSconto(models.Model):
    codice = models.CharField(max_length=50, blank=True, default='')
    descrizione = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.tiposconto'
        verbose_name = 'Tipo Sconto'
        verbose_name_plural = 'Tipi Sconto'

    def __str__(self):
        return f"{self.codice} - {self.descrizione}"


class MettereInTipoFron(models.Model):
    CdArticolo = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_tipofron'
        verbose_name = 'Mettere TipoFron'
        verbose_name_plural = 'Mettere TipoFron'

    def __str__(self):
        return self.CdArticolo