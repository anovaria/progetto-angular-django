from django.db import models


class ListaInventario(models.Model):
    """
    Articoli rilevati durante la sessione di inventario.
    Equivalente a dbo.t_listaarticoli in GoldCursori.
    Tabella fisica: [cursori].[lista_inventario] — creata via RunSQL nella migration.
    """
    numero_richiesta = models.CharField(max_length=50, db_index=True)
    cod_articolo = models.CharField(max_length=20)
    descrizione = models.CharField(max_length=200, blank=True)
    qtar = models.CharField(max_length=30, blank=True)    # quantità rilevata
    cd_ean = models.CharField(max_length=20, blank=True)
    elab = models.CharField(max_length=2, default='0')    # '0'=da elab, '1'=elaborato
    tipo_articolo = models.CharField(max_length=30, blank=True)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'cursori.lista_inventario'

    def __str__(self):
        return f"{self.cod_articolo} - {self.descrizione}"


class PosArticoliGlob(models.Model):
    """
    Posizionamento articoli (corsia/campata/facing/min/max).
    Equivalente a dbo.t_posArticoliglob in GoldCursori.
    elaborato: 'N'=bozza, 'S'=confermato, 'D'=da eliminare.
    Il record con numero_richiesta='GLOBAL' rappresenta la posizione corrente definitiva.
    Tabella fisica: [cursori].[pos_articoli_glob] — creata via RunSQL nella migration.
    """
    numero_richiesta = models.CharField(max_length=50, db_index=True)
    corsia = models.CharField(max_length=20, blank=True)
    campata = models.CharField(max_length=20, blank=True)
    cod_articolo = models.CharField(max_length=20, db_index=True)
    descrizione = models.CharField(max_length=200, blank=True)
    stato = models.CharField(max_length=10, blank=True)
    pz_xcrt = models.CharField(max_length=10, blank=True)
    ean = models.CharField(max_length=20, blank=True)
    qta = models.CharField(max_length=10, blank=True)
    mini = models.CharField(max_length=10, blank=True)
    max_val = models.CharField(max_length=10, blank=True)
    facing = models.CharField(max_length=10, blank=True)
    elaborato = models.CharField(max_length=2, default='N')
    ip = models.CharField(max_length=40, blank=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    aggiornato_il = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'cursori.pos_articoli_glob'

    def __str__(self):
        return f"{self.cod_articolo} Co:{self.corsia} Ca:{self.campata}"


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
    bl = models.CharField(max_length=20, blank=True)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'cursori.stampa_cursori'
        ordering = ['id']

    def get_tipo_label(self) -> str:
        return self.bl or ''

    def __str__(self):
        return f"{self.cod_articolo} x{self.num_cursori}"
