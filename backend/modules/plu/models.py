# modules/plu/models.py
from django.db import models


class Reparto(models.Model):
    """
    Model per la tabella t_Reparti
    """
    class Meta:
        managed = False
        db_table = 't_Reparti'
        verbose_name = 'Reparto'
        verbose_name_plural = 'Reparti'
        ordering = ['NrReparto']
    
    id = models.AutoField(primary_key=True, db_column='ID')
    dtaaggio = models.CharField(max_length=10, db_column='dtaaggio', null=True, blank=True)
    NrReparto = models.CharField(max_length=13, db_column='NrReparto')
    RepDescrizione = models.CharField(max_length=50, db_column='RepDescrizione')
    DataCreazione = models.DateTimeField(db_column='DataCreazione', null=True, blank=True)
    
    def __str__(self):
        return f"{self.NrReparto} - {self.RepDescrizione}"


class RepartoPlu(models.Model):
    """
    Model per la VIEW esistente V_RepartoPlu
    """
    
    class Meta:
        managed = False
        db_table = 'V_RepartoPlu'
        verbose_name = 'Reparto PLU'
        verbose_name_plural = 'Reparti PLU'
        ordering = ['rep', 'codArticolo']
    
    ccom = models.CharField(
        max_length=4000, 
        db_column='CCOM', 
        null=True, 
        blank=True,
        verbose_name='Codice Fornitore'
    )
    descrccom = models.CharField(
        max_length=4000, 
        db_column='DESCRCCOM', 
        null=True, 
        blank=True, 
        verbose_name='Fornitore'
    )
    rep = models.CharField(
        max_length=13,
        db_column='REP', 
        null=True,
        blank=True,
        verbose_name='Reparto'
    )
    codArticolo = models.CharField(
        max_length=13,
        db_column='codArticolo',
        primary_key=True, 
        verbose_name='Codice Articolo'
    )
    descrizione = models.CharField(
        max_length=4000, 
        db_column='descrizione',
        null=True,
        blank=True,
        verbose_name='Descrizione'
    )
    bancobilancia = models.CharField(
        max_length=2, 
        db_column='Bancobilancia', 
        null=True,
        blank=True,
        verbose_name='Banco Bilancia'
    )
    plu = models.CharField(
        max_length=7, 
        db_column='plu',
        null=True,
        blank=True, 
        verbose_name='PLU'
    )
    ean = models.CharField(
        max_length=14,
        db_column='EAN', 
        null=True, 
        blank=True, 
        verbose_name='EAN'
    )
    
    def __str__(self):
        return f"PLU {self.plu} - {self.descrizione}"
    
    @property
    def plu_int(self):
        """Restituisce PLU come intero"""
        try:
            return int(self.plu) if self.plu else 0
        except (ValueError, TypeError):
            return 0
    
    @property
    def ean_formatted(self):
        """EAN formattato (13 cifre con padding)"""
        if self.ean:
            return str(self.ean).zfill(13)
        return ''