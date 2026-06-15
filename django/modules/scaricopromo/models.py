"""
Scarico Promo - Models
App per gestione promozioni freschi: cambio stato attributi articolo ed export CSV.
Migrazione da Access PromoDb.accdb + flusso reparto (Gp-Client-New).
"""
from django.db import models


# ============================================================
# TABELLE LINKED (SQL Server Gold - SOLA LETTURA)
# Queste vengono lette dal DB goldreport tramite il router
# ============================================================

class SargcAttributi(models.Model):
    """
    dbo_t_SARGC - Attributi articolo dal gestionale Gold.
    """
    DTAAGGIO = models.CharField(max_length=50, blank=True, default='')
    S = models.CharField(max_length=10, blank=True, default='')
    REP = models.CharField(max_length=10, blank=True, default='')
    SREP = models.CharField(max_length=10, blank=True, default='')
    FAM = models.CharField(max_length=10, blank=True, default='')
    CODART = models.CharField(max_length=50, blank=True, default='', db_index=True)
    DESCRIZIONE_ART = models.CharField(max_length=255, blank=True, default='')
    GIACPDV = models.FloatField(default=0)
    GIACDEPCOLLI = models.FloatField(default=0)
    ST = models.CharField(max_length=10, blank=True, default='')
    COD = models.CharField(max_length=50, blank=True, default='')
    ALPHA = models.CharField(max_length=255, blank=True, default='')
    DTAINI = models.CharField(max_length=50, blank=True, default='')
    DTAFINE = models.CharField(max_length=50, blank=True, default='')
    DTACH = models.CharField(max_length=50, blank=True, default='')
    DataCreazione = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 't_SARGC'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CODART} - ST:{self.ST}"


class ArticoliGiacTutti(models.Model):
    """
    dbo_t_ArticoliGiacTutti - Giacenze articoli dal gestionale Gold.
    """
    DTAAGGIO = models.CharField(max_length=50, blank=True, default='')
    SETTORE = models.CharField(max_length=50, blank=True, default='')
    DESCRSETTORE = models.CharField(max_length=255, blank=True, default='')
    REP = models.CharField(max_length=10, blank=True, default='')
    DESCRREP = models.CharField(max_length=255, blank=True, default='')
    CODARTICOLO = models.CharField(max_length=50, blank=True, default='', db_index=True)
    DESCRART = models.CharField(max_length=255, blank=True, default='')
    STATO = models.CharField(max_length=10, blank=True, default='')
    GIAC_PDV = models.FloatField(default=0)
    ULTIMA_VENDITA = models.CharField(max_length=50, blank=True, default='')
    GIAC_DEP = models.FloatField(default=0)
    GIAC_DEPCARED = models.FloatField(default=0)
    DataCreazione = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 't_ArticoliGiacTutti'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CODARTICOLO} - {self.DESCRART}"


class ChOrdine(models.Model):
    """
    dbo_T_chOrdine - Tabella ordini su Gold.
    """
    Ccom = models.CharField(max_length=50, blank=True, default='')
    CodArticolo = models.CharField(max_length=50, blank=True, default='')
    flag = models.CharField(max_length=10, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'T_chOrdine'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.Ccom} - {self.CodArticolo}"


class VartPromoFuture(models.Model):
    """
    dbo.v_ArtPromoFuture - View promozioni future.
    Fonte principale per selezione articoli in promozione.
    """
    SETTORE = models.CharField(max_length=26, blank=True, default='')
    REPARTO = models.CharField(max_length=26, blank=True, default='')
    DESCREP = models.CharField(max_length=100, blank=True, default='')
    SOTTOREPARTO = models.CharField(max_length=26, blank=True, default='')
    DESCSREP = models.CharField(max_length=100, blank=True, default='')
    CODFORN = models.CharField(max_length=255, blank=True, default='')
    DESCFORN = models.CharField(max_length=255, blank=True, default='')
    OPLCEXOPR = models.CharField(max_length=26, blank=True, default='')
    DTAINI = models.CharField(max_length=20, blank=True, default='')
    DTAFINE = models.CharField(max_length=20, blank=True, default='')
    ARVCEXR = models.CharField(max_length=26, blank=True, default='', db_index=True)
    ARCCODE = models.CharField(max_length=28, blank=True, default='')
    PRZ_OFF = models.FloatField(default=0)
    GIACENZA_PDV = models.FloatField(default=0)
    QTA_IN_ORDINE = models.FloatField(default=0)
    ULTIMO_ORDINE = models.CharField(max_length=20, blank=True, default='')
    CCOM = models.FloatField(default=0)
    DESCRCCOM = models.CharField(max_length=255, blank=True, default='')
    EANPRINC = models.FloatField(default=0)
    STATO = models.CharField(max_length=16, blank=True, default='')
    prz_std = models.FloatField(default=0)
    FAMIGLIA = models.CharField(max_length=26, blank=True, default='')
    DESCFAM = models.CharField(max_length=100, blank=True, default='')
    CODARTFO = models.CharField(max_length=40, blank=True, default='')
    BUYER = models.CharField(max_length=30, blank=True, default='')
    Expr1 = models.CharField(max_length=32, blank=True, default='')
    CODPIANO = models.FloatField(default=0)
    GEST = models.CharField(max_length=255, blank=True, default='')
    GIACENZA_DEPOSITO = models.FloatField(default=0)
    VL = models.CharField(max_length=6, blank=True, default='')
    INDPICK = models.CharField(max_length=30, blank=True, default='')
    CARTPALL = models.FloatField(default=0)
    PZXCART = models.FloatField(default=0)
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    DESCRIPTION = models.CharField(max_length=255, blank=True, default='')
    Descrizione = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'v_ArtPromoFuture'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.ARVCEXR} - {self.Descrizione}"


class VallArticolo(models.Model):
    """
    dbo.v_AllArticolo - Anagrafica articoli con EAN.
    """
    EANPRINC = models.FloatField(default=0)
    EAN = models.CharField(max_length=28, blank=True, default='')
    STATO = models.CharField(max_length=16, blank=True, default='')
    PREZZOVEND = models.FloatField(default=0)
    GIACENZA_PDV = models.FloatField(default=0)
    GIACENZA_DEPOSITO = models.FloatField(default=0)
    CODART = models.CharField(max_length=26, blank=True, default='', db_index=True)
    DESCRART = models.CharField(max_length=255, blank=True, default='')
    TIPO = models.FloatField(default=0)

    class Meta:
        managed = False
        db_table = 'v_AllArticolo'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CODART} - {self.DESCRART}"


class MasterData(models.Model):
    """
    dbo.t_masterData - Dati articolo completi.
    """
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    SETTORE = models.CharField(max_length=26, blank=True, default='')
    REPARTO = models.CharField(max_length=26, blank=True, default='')
    DESCREP = models.CharField(max_length=100, blank=True, default='')
    SOTTOREPARTO = models.CharField(max_length=26, blank=True, default='')
    DESCSREP = models.CharField(max_length=100, blank=True, default='')
    FAMIGLIA = models.CharField(max_length=26, blank=True, default='')
    DESCFAM = models.CharField(max_length=100, blank=True, default='')
    CODFORN = models.CharField(max_length=255, blank=True, default='')
    DESCFORN = models.CharField(max_length=255, blank=True, default='')
    CCOM = models.CharField(max_length=255, blank=True, default='')
    DESCRCCOM = models.CharField(max_length=255, blank=True, default='')
    CODARTFO = models.CharField(max_length=40, blank=True, default='')
    CODART = models.CharField(max_length=26, blank=True, default='', db_index=True)
    TIPOA = models.FloatField(default=0)
    DESCRART = models.CharField(max_length=255, blank=True, default='')
    GEST = models.CharField(max_length=255, blank=True, default='')
    PZXCART = models.FloatField(default=0)
    PRZ_VEND = models.FloatField(default=0)
    GIACENZA_PDV = models.FloatField(default=0)
    GIACENZA_DEPOSITO = models.FloatField(default=0)
    QTA_IN_ORDINE = models.FloatField(default=0)
    ULTIMO_ORDINE = models.CharField(max_length=20, blank=True, default='')
    DATA_CONSEGNA = models.CharField(max_length=20, blank=True, default='')
    ULTIMA_VENDITA = models.CharField(max_length=20, blank=True, default='')
    ULTIMO_RICEVIMENTO = models.CharField(max_length=20, blank=True, default='')
    QTA_RESO = models.FloatField(default=0)
    VAL_RESO = models.FloatField(default=0)
    CODPROMO = models.CharField(max_length=255, blank=True, default='')
    S = models.CharField(max_length=16, blank=True, default='')
    TCOL = models.CharField(max_length=176, blank=True, default='')
    IVA = models.FloatField(default=0)
    VL = models.FloatField(default=0)
    PRZPROMO = models.FloatField(default=0)
    ULC = models.FloatField(default=0)
    GIAC_DEPCARED = models.FloatField(default=0)
    DataCreazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_masterData'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CODART} - {self.DESCRART}"


class PianoPromo(models.Model):
    """
    dbo.t_PianoPromo - Piani promozionali.
    """
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    CODICEGOLD = models.FloatField(default=0)
    PIANO = models.CharField(max_length=26, blank=True, default='')
    DESCRIZIONE = models.CharField(max_length=100, blank=True, default='')
    INIZIO_SELLIN = models.CharField(max_length=20, blank=True, default='')
    FINE_SELLIN = models.CharField(max_length=20, blank=True, default='')
    INIZIO_SELLOUT = models.CharField(max_length=20, blank=True, default='')
    FINE_SELLOUT = models.CharField(max_length=20, blank=True, default='')
    CODPIANO = models.FloatField(default=0)
    DataCreazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_PianoPromo'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.PIANO} - {self.DESCRIZIONE}"


class RecuperaPromo(models.Model):
    """
    dbo.t_recuperapromo - Per duplica promo da storico.
    """
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    CODGOLD = models.FloatField(default=0)
    OPLCEXOPR = models.CharField(max_length=26, blank=True, default='')
    DESCPIANO = models.CharField(max_length=100, blank=True, default='')
    DTAINI = models.CharField(max_length=20, blank=True, default='')
    DTAFINE = models.CharField(max_length=20, blank=True, default='')
    REP = models.CharField(max_length=26, blank=True, default='')
    CODFORN = models.CharField(max_length=255, blank=True, default='')
    CCOM = models.CharField(max_length=255, blank=True, default='')
    DESCRCCOM = models.CharField(max_length=255, blank=True, default='')
    CODARTFO = models.CharField(max_length=4, blank=True, default='')
    CODART = models.CharField(max_length=26, blank=True, default='')
    DESCRARTICOLO = models.CharField(max_length=255, blank=True, default='')
    EAN = models.CharField(max_length=28, blank=True, default='')
    ST = models.CharField(max_length=4, blank=True, default='')
    TCOL = models.CharField(max_length=176, blank=True, default='')
    VL = models.FloatField(default=0)
    PRZ_VEND = models.FloatField(default=0)
    PRZ_OFF = models.FloatField(default=0)
    DataCreazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_recuperapromo'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CODART} - {self.DESCRARTICOLO}"


class Reparti(models.Model):
    """
    dbo.t_Reparti - Anagrafica reparti.
    """
    dtaaggio = models.CharField(max_length=20, blank=True, default='')
    NrReparto = models.CharField(max_length=26, blank=True, default='')
    RepDescrizione = models.CharField(max_length=100, blank=True, default='')
    DataCreazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_Reparti'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.NrReparto} - {self.RepDescrizione}"


class Ean(models.Model):
    """
    dbo.t_t_Ean - EAN articoli.
    """
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    CODART = models.CharField(max_length=26, blank=True, default='', db_index=True)
    DESCRART = models.CharField(max_length=255, blank=True, default='')
    EAN = models.CharField(max_length=28, blank=True, default='')
    EANA = models.CharField(max_length=38, blank=True, default='')
    TIPO = models.FloatField(default=0)
    PRINC = models.FloatField(default=0)
    STEAN = models.FloatField(default=0)
    DTAINI = models.CharField(max_length=20, blank=True, default='')
    STAFINE = models.CharField(max_length=20, blank=True, default='')
    GEST = models.CharField(max_length=255, blank=True, default='')
    DataCreazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_t_Ean'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CODART} - {self.EAN}"


class Noscorep(models.Model):
    """
    dbo.t_NOSCOREP - Attributo speciale no scorep.
    """
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    S = models.CharField(max_length=26, blank=True, default='')
    REP = models.CharField(max_length=26, blank=True, default='')
    SREP = models.CharField(max_length=26, blank=True, default='')
    FAM = models.CharField(max_length=26, blank=True, default='')
    LINEA_PRODOTTO = models.CharField(max_length=255, blank=True, default='')
    DESCR_LINEA = models.CharField(max_length=255, blank=True, default='')
    CCOM = models.CharField(max_length=255, blank=True, default='')
    DESCRCCOM = models.CharField(max_length=255, blank=True, default='')
    CODART = models.CharField(max_length=26, blank=True, default='', db_index=True)
    DESCRIZIONE_ART = models.CharField(max_length=255, blank=True, default='')
    GIACPDV = models.FloatField(default=0)
    NOSC = models.CharField(max_length=16, blank=True, default='')
    CODSC = models.CharField(max_length=16, blank=True, default='')
    DTAINISC = models.CharField(max_length=20, blank=True, default='')
    DTACHISC = models.CharField(max_length=20, blank=True, default='')
    DTACH = models.CharField(max_length=20, blank=True, default='')
    TCOL = models.CharField(max_length=16, blank=True, default='')
    COLLE = models.CharField(max_length=160, blank=True, default='')
    STATOART = models.CharField(max_length=16, blank=True, default='')
    DTACHIUSSARGC = models.CharField(max_length=20, blank=True, default='')
    DataCreazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_NOSCOREP'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CODART} - {self.CODSC}"


class ArtFrePromo(models.Model):
    """
    dbo.t_artfrepromo - Articoli freschi promo.
    """
    DTAAGGIO = models.CharField(max_length=20, blank=True, default='')
    REP = models.CharField(max_length=26, blank=True, default='')
    DESCREP = models.CharField(max_length=100, blank=True, default='')
    CODFO = models.CharField(max_length=255, blank=True, default='')
    RAGIONESOCIALE = models.CharField(max_length=255, blank=True, default='')
    CCOM = models.CharField(max_length=255, blank=True, default='')
    DIVISIONE = models.CharField(max_length=255, blank=True, default='')
    LINEA_PRODOTTO = models.CharField(max_length=255, blank=True, default='')
    DESCR_LINEA = models.CharField(max_length=255, blank=True, default='')
    TIPO_RIORDINO = models.CharField(max_length=255, blank=True, default='')
    ARTFO = models.CharField(max_length=40, blank=True, default='')
    CEXR = models.CharField(max_length=26, blank=True, default='', db_index=True)
    DESC_CEXR = models.CharField(max_length=255, blank=True, default='')
    PRZ_VEND = models.FloatField(default=0)
    VL = models.FloatField(default=0)
    DataCreazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 't_artfrepromo'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CEXR} - {self.DESC_CEXR}"


class Attrib1(models.Model):
    """
    dbo.t_Attrib1 - Scrittura attributi su Gold.
    """
    CodArticolo = models.CharField(max_length=26, blank=True, default='')
    ClasseAttri = models.CharField(max_length=16, blank=True, default='')
    CodiceAttri = models.CharField(max_length=16, blank=True, default='')
    ValNumerico = models.CharField(max_length=22, blank=True, default='')
    ValAlpha = models.CharField(max_length=160, blank=True, default='')
    ValData = models.CharField(max_length=20, blank=True, default='')
    DtaIni = models.CharField(max_length=40, blank=True, default='')
    DtaFin = models.CharField(max_length=40, blank=True, default='')
    Flag1 = models.CharField(max_length=20, blank=True, null=True, default='')
    note = models.CharField(max_length=40, blank=True, null=True, default='')

    class Meta:
        managed = False
        db_table = 't_Attrib1'
        app_label = 'goldreport_mssql'

    def __str__(self):
        return f"{self.CodArticolo} - {self.CodiceAttri}"


# ============================================================
# TABELLE LOCALI (DjangoIntranet - schema scaricopromo)
# ============================================================

class MettereInBase(models.Model):
    """Classe base astratta per le tabelle 'Mettere in X'."""
    codart = models.CharField('Codice Articolo', max_length=50, blank=True, default='')

    class Meta:
        abstract = True

    def __str__(self):
        return self.codart


class MettereInA(MettereInBase):
    """Articoli da mettere in stato A (con codice commerciale)."""
    ccom = models.CharField('Codice Commerciale', max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_a'
        verbose_name = 'Mettere in A'
        verbose_name_plural = 'Mettere in A'


class MettereInE(MettereInBase):
    """Articoli da mettere in stato E."""
    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_e'
        verbose_name = 'Mettere in E'
        verbose_name_plural = 'Mettere in E'


class MettereInF(MettereInBase):
    """Articoli da mettere in stato F."""
    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_f'
        verbose_name = 'Mettere in F'
        verbose_name_plural = 'Mettere in F'


class MettereInI(MettereInBase):
    """Articoli da mettere in stato I (con codice commerciale)."""
    ccom = models.CharField('Codice Commerciale', max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_i'
        verbose_name = 'Mettere in I'
        verbose_name_plural = 'Mettere in I'


class MettereInK(MettereInBase):
    """Articoli da mettere in stato K."""
    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_k'
        verbose_name = 'Mettere in K'
        verbose_name_plural = 'Mettere in K'


class MettereInS(MettereInBase):
    """Articoli da mettere in stato S."""
    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_s'
        verbose_name = 'Mettere in S'
        verbose_name_plural = 'Mettere in S'


class NonPossoMettereInA(models.Model):
    """Articoli con giacenza che non possono essere messi in A."""
    codart = models.CharField('Codice Articolo', max_length=50, blank=True, default='')
    ccom = models.CharField('Codice Commerciale', max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.nonposso_a'
        verbose_name = 'Non posso mettere in A'
        verbose_name_plural = 'Non posso mettere in A'

    def __str__(self):
        return f"{self.codart} ({self.ccom})"


class ChiudiAttri(models.Model):
    """
    Tabella temporanea per chiusura attributi.
    """
    CodArticolo = models.CharField(max_length=50, blank=True, default='')
    ClasseAttri = models.CharField(max_length=50, blank=True, default='')
    CodAttri = models.CharField(max_length=10, blank=True, default='')
    ValoreNum = models.CharField(max_length=50, blank=True, default='')
    ValoreAlpha = models.CharField(max_length=255, blank=True, default='')
    ValoreData = models.CharField(max_length=50, blank=True, default='')
    DtaIniz = models.CharField(max_length=50, blank=True, default='')
    DTACH = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.chiudiattri'
        verbose_name = 'Chiudi Attributo'
        verbose_name_plural = 'Chiudi Attributi'

    def __str__(self):
        return f"{self.CodArticolo} - {self.CodAttri}"


class ApriAttri(models.Model):
    """
    Tabella temporanea per apertura attributi.
    """
    CodArticolo = models.CharField(max_length=50, blank=True, default='')
    ClasseAttri = models.CharField(max_length=50, blank=True, default='')
    CodAttri = models.CharField(max_length=10, blank=True, default='')
    ValoreNum = models.CharField(max_length=50, blank=True, default='')
    ValoreAlpha = models.CharField(max_length=255, blank=True, default='')
    ValoreData = models.CharField(max_length=50, blank=True, default='')
    dtaini = models.CharField(max_length=50, blank=True, default='')
    dtaFine = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.apriattri'
        verbose_name = 'Apri Attributo'
        verbose_name_plural = 'Apri Attributi'

    def __str__(self):
        return f"{self.CodArticolo} - {self.CodAttri}"


class AggiornaAttri(models.Model):
    """
    Tabella di consolidamento: unisce chiusure e aperture attributi.
    """
    CodArticolo = models.CharField(max_length=50, blank=True, default='')
    ClasseAttri = models.CharField(max_length=50, blank=True, default='')
    CodAttri = models.CharField(max_length=10, blank=True, default='')
    ValoreNum = models.CharField(max_length=50, blank=True, default='')
    ValoreAlpha = models.CharField(max_length=255, blank=True, default='')
    ValoreData = models.CharField(max_length=50, blank=True, default='')
    dtaini = models.CharField(max_length=50, blank=True, default='')
    dtaFine = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.aggiornaattri'
        verbose_name = 'Aggiorna Attributo'
        verbose_name_plural = 'Aggiorna Attributi'

    def __str__(self):
        return f"{self.CodArticolo} - {self.CodAttri}"


class PerExport(models.Model):
    """
    Dati promozione per export CSV.
    """
    Promozioni = models.CharField(max_length=255, blank=True, default='')
    FornitoreAmministrativo = models.CharField(max_length=255, blank=True, default='')
    ContrattoCommerciale = models.CharField(max_length=255, blank=True, default='')
    RagioneSociale = models.CharField(max_length=255, blank=True, default='')
    CodiceProdotto = models.CharField(max_length=50, blank=True, default='', db_index=True)
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
    Meccanicav = models.CharField(max_length=50, blank=True, default='')
    Valore = models.CharField(max_length=50, blank=True, default='')
    Valore1 = models.CharField(max_length=50, blank=True, default='')
    export = models.CharField(max_length=50, blank=True, default='')
    QtaOmaggio = models.CharField(max_length=50, blank=True, default='')
    pianoB = models.CharField(max_length=50, blank=True, default='')
    vl = models.CharField('Variante Logistica', max_length=50, blank=True, default='')
    DATAEXPORT = models.CharField(max_length=50, blank=True, default='')
    utenteWind = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.perexport'
        verbose_name = 'Export Promozione'
        verbose_name_plural = 'Export Promozioni'

    def __str__(self):
        return f"{self.CodiceProdotto} - {self.DescrizioneProdotto}"


class PerExportStorico(models.Model):
    """Storico degli export effettuati."""
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
    Meccanicav = models.CharField(max_length=50, blank=True, default='')
    Valore = models.CharField(max_length=50, blank=True, default='')
    Valore1 = models.CharField(max_length=50, blank=True, default='')
    export = models.CharField(max_length=50, blank=True, default='')
    QtaOmaggio = models.CharField(max_length=50, blank=True, default='')
    pianoB = models.CharField(max_length=50, blank=True, default='')
    VL = models.CharField(max_length=50, blank=True, default='')
    DATAEXPORT = models.CharField(max_length=50, blank=True, default='')
    utenteWind = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.perexport_storico'
        verbose_name = 'Export Storico'
        verbose_name_plural = 'Export Storici'

    def __str__(self):
        return f"{self.CodiceProdotto} - {self.DATAEXPORT}"


# ============================================================
# TABELLE LOCALI REPARTO (DjangoIntranet - schema scaricopromo)
# ============================================================

class ArtFreFase1(models.Model):
    """
    Articoli freschi selezionati in Fase 1.
    Popolata da v_ArtPromoFuture o v_ArtFrePromo filtrata per CCOM.
    """
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

    class Meta:
        managed = False
        db_table = 'scaricopromo.artfrefase1'
        verbose_name = 'Articolo Fase 1'
        verbose_name_plural = 'Articoli Fase 1'

    def __str__(self):
        return f"{self.CEXR} - {self.DESC_CEXR}"


class ArtDaVerificare(models.Model):
    """
    Articoli da verificare prima dell'export.
    """
    Promozioni = models.CharField(max_length=255, blank=True, default='')
    FornitoreAmministrativo = models.CharField(max_length=255, blank=True, default='')
    ContrattoCommerciale = models.CharField(max_length=255, blank=True, default='')
    RagioneSociale = models.CharField(max_length=255, blank=True, default='')
    CodiceProdotto = models.CharField(max_length=50, blank=True, default='')
    DescrizioneProdotto = models.CharField(max_length=255, blank=True, default='')
    SelezionePromozione = models.CharField(max_length=255, blank=True, default='')
    DataInizio = models.CharField(max_length=50, blank=True, default='')
    DataFine = models.CharField(max_length=50, blank=True, default='')
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

    class Meta:
        managed = False
        db_table = 'scaricopromo.artdaverificare'
        verbose_name = 'Articolo da Verificare'
        verbose_name_plural = 'Articoli da Verificare'

    def __str__(self):
        return f"{self.CodiceProdotto} - {self.DescrizioneProdotto}"


class CodArtPromo(models.Model):
    """
    Codici articolo inseriti manualmente per promo.
    """
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
    """
    Articoli importati da file per promo.
    """
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
    """
    Lookup meccaniche promozionali.
    """
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
    """
    Lookup tipi sconto.
    """
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
    """
    Per cambio tipo frontale.
    """
    CdArticolo = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        managed = False
        db_table = 'scaricopromo.metterein_tipofron'
        verbose_name = 'Mettere TipoFron'
        verbose_name_plural = 'Mettere TipoFron'

    def __str__(self):
        return self.CdArticolo