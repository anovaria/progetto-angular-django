from django.db import models


class StampaCursori(models.Model):
    """
    Coda stampa frontalini.
    Equivalente a dbo.t_StampaCursori in GoldCursori.
    Tabella fisica: [cursori].[stampa_cursori] — creata via RunSQL nella migration.
    """
    numero_richiesta = models.CharField(max_length=50, db_index=True)
    cod_articolo = models.CharField(max_length=20)
    descrizione = models.CharField(max_length=200, blank=True)
    num_cursori = models.IntegerField(default=1)
    ean = models.CharField(max_length=20, blank=True)
    codartfo = models.CharField(max_length=30, blank=True)
    prezzo_vend = models.CharField(max_length=20, blank=True)
    giac_pdv = models.CharField(max_length=20, blank=True)
    giac_dep = models.CharField(max_length=20, blank=True)
    ccom = models.CharField(max_length=20, blank=True)
    descrccom = models.CharField(max_length=100, blank=True)
    codforn = models.CharField(max_length=20, blank=True)
    descforn = models.CharField(max_length=100, blank=True)
    elaborato = models.CharField(max_length=5, default='NO')  # 'NO' / 'SI'
    ip = models.CharField(max_length=40, blank=True)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'cursori.stampa_cursori'
        ordering = ['id']

    def __str__(self):
        return f"{self.cod_articolo} x{self.num_cursori}"
