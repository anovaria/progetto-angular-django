"""
Scarico Promo - Models
App per gestione promozioni freschi: cambio stato attributi articolo ed export CSV.
Migrazione da Access PromoDb.accdb
"""
from django.db import models


# ============================================================
# TABELLE LINKED (SQL Server Gold - SOLA LETTURA)
# Queste vengono lette dal DB goldreport tramite il router
# ============================================================

class SargcAttributi(models.Model):
    """
    dbo_t_SARGC - Attributi articolo dal gestionale Gold.
    Tabella linked in Access, read-only.
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
    Tabella linked in Access, read-only.
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
    In Access era linked e ci si scriveva con q_accodaDaMettereASql.
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


# ============================================================
# TABELLE LOCALI (DjangoIntranet - LETTURA/SCRITTURA)
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
        db_table = 'scaricopromo_metterein_a'
        verbose_name = 'Mettere in A'
        verbose_name_plural = 'Mettere in A'


class MettereInE(MettereInBase):
    """Articoli da mettere in stato E."""
    class Meta:
        db_table = 'scaricopromo_metterein_e'
        verbose_name = 'Mettere in E'
        verbose_name_plural = 'Mettere in E'


class MettereInF(MettereInBase):
    """Articoli da mettere in stato F."""
    class Meta:
        db_table = 'scaricopromo_metterein_f'
        verbose_name = 'Mettere in F'
        verbose_name_plural = 'Mettere in F'


class MettereInI(MettereInBase):
    """Articoli da mettere in stato I (con codice commerciale)."""
    ccom = models.CharField('Codice Commerciale', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'scaricopromo_metterein_i'
        verbose_name = 'Mettere in I'
        verbose_name_plural = 'Mettere in I'


class MettereInK(MettereInBase):
    """Articoli da mettere in stato K."""
    class Meta:
        db_table = 'scaricopromo_metterein_k'
        verbose_name = 'Mettere in K'
        verbose_name_plural = 'Mettere in K'


class MettereInS(MettereInBase):
    """Articoli da mettere in stato S."""
    class Meta:
        db_table = 'scaricopromo_metterein_s'
        verbose_name = 'Mettere in S'
        verbose_name_plural = 'Mettere in S'


class NonPossoMettereInA(models.Model):
    """Articoli con giacenza che non possono essere messi in A."""
    codart = models.CharField('Codice Articolo', max_length=50, blank=True, default='')
    ccom = models.CharField('Codice Commerciale', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'scaricopromo_nonposso_a'
        verbose_name = 'Non posso mettere in A'
        verbose_name_plural = 'Non posso mettere in A'

    def __str__(self):
        return f"{self.codart} ({self.ccom})"


class ChiudiAttri(models.Model):
    """
    Tabella temporanea per chiusura attributi.
    Popolata dalle query ChiudiAttri-X che leggono da 'Mettere in X' + dbo_t_SARGC.
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
        db_table = 'scaricopromo_chiudiattri'
        verbose_name = 'Chiudi Attributo'
        verbose_name_plural = 'Chiudi Attributi'

    def __str__(self):
        return f"{self.CodArticolo} - {self.CodAttri}"


class ApriAttri(models.Model):
    """
    Tabella temporanea per apertura attributi.
    Popolata dalle query q_ApriAttri-X (nuovo stato, data inizio = DTACH+1, fine 31/12/2049).
    """
    CodArticolo = models.CharField(max_length=50, blank=True, default='')
    ClasseAttri = models.CharField(max_length=50, blank=True, default='')
    CodAttri = models.CharField(max_length=10, blank=True, default='')
    ValoreNum = models.CharField(max_length=50, blank=True, default='')
    ValoreAlpha = models.CharField(max_length=255, blank=True, default='')
    ValoreData = models.CharField(max_length=50, blank=True, default='')
    dtaini = models.DateTimeField(null=True, blank=True)
    dtaFine = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'scaricopromo_apriattri'
        verbose_name = 'Apri Attributo'
        verbose_name_plural = 'Apri Attributi'

    def __str__(self):
        return f"{self.CodArticolo} - {self.CodAttri}"


class AggiornaAttri(models.Model):
    """
    Tabella di consolidamento: unisce chiusure e aperture attributi.
    Usata per generare il CSV di export verso Gold.
    """
    CodArticolo = models.CharField(max_length=50, blank=True, default='')
    ClasseAttri = models.CharField(max_length=50, blank=True, default='')
    CodAttri = models.CharField(max_length=10, blank=True, default='')
    ValoreNum = models.CharField(max_length=50, blank=True, default='')
    ValoreAlpha = models.CharField(max_length=255, blank=True, default='')
    ValoreData = models.CharField(max_length=50, blank=True, default='')
    dtaini = models.DateTimeField(null=True, blank=True)
    dtaFine = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'scaricopromo_aggiornaattri'
        verbose_name = 'Aggiorna Attributo'
        verbose_name_plural = 'Aggiorna Attributi'

    def __str__(self):
        return f"{self.CodArticolo} - {self.CodAttri}"


class PerExport(models.Model):
    """
    Dati promozione per export CSV.
    Tabella principale visualizzata nella sottomaschera sm_Esporta.
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
        db_table = 'scaricopromo_perexport'
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
        db_table = 'scaricopromo_perexport_storico'
        verbose_name = 'Export Storico'
        verbose_name_plural = 'Export Storici'

    def __str__(self):
        return f"{self.CodiceProdotto} - {self.DATAEXPORT}"
