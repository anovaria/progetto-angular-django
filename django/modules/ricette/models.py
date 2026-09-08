from django.db import models
from decimal import Decimal


class Ricetta(models.Model):
    DIFFICOLTA = [('bassa', 'Bassa'), ('media', 'Media'), ('alta', 'Alta')]

    codice_articolo         = models.CharField(max_length=50, blank=True)
    descrizione             = models.CharField(max_length=200)
    categoria               = models.CharField(max_length=100, blank=True)
    difficolta              = models.CharField(max_length=20, choices=DIFFICOLTA, default='media', blank=True)
    ean                     = models.CharField(max_length=50, blank=True)

    # Confezione
    tipo_contenitore        = models.CharField(max_length=100, blank=True)
    dimensioni_contenitore  = models.CharField(max_length=100, blank=True)
    grammatura_media_kg     = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    shelf_life              = models.CharField(max_length=200, blank=True)
    conservabilita          = models.CharField(max_length=200, blank=True)

    # Nutrizionali (per 100g)
    kcal                    = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    protidi                 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    lipidi                  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    glucidi                 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Produzione
    calo_peso_pct           = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    quantita_prodotta_kg    = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    porzione_media_kg       = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)

    # Lavoro
    tempo_produzione_min    = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    costo_al_minuto         = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # Prezzo
    prezzo_vendita_iva      = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    aliquota_iva            = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Note
    ingredienti_etichetta   = models.TextField(blank=True)
    modalita_preparazione   = models.TextField(blank=True)
    abbinamenti             = models.TextField(blank=True)
    consigli_cottura        = models.TextField(blank=True)
    note                    = models.TextField(blank=True)

    # Meta
    creato_da               = models.CharField(max_length=100, blank=True)
    creato_il               = models.DateTimeField(auto_now_add=True)
    aggiornato_il           = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['descrizione']
        verbose_name = 'Ricetta'
        verbose_name_plural = 'Ricette'

    def __str__(self):
        return f"{self.codice_articolo} – {self.descrizione}" if self.codice_articolo else self.descrizione

    # ── Calcoli conto economico ───────────────────────────────────────────────

    @property
    def costo_totale_mp(self):
        return sum((i.importo_totale or Decimal('0')) for i in self.ingredienti.all())

    @property
    def costo_totale_imballi(self):
        return sum((i.importo_totale or Decimal('0')) for i in self.imballaggi.all())

    @property
    def costo_totale_lavoro(self):
        if self.tempo_produzione_min and self.costo_al_minuto:
            return self.tempo_produzione_min * self.costo_al_minuto
        return Decimal('0')

    @property
    def quantita_effettiva_kg(self):
        if not self.quantita_prodotta_kg:
            return None
        calo = self.calo_peso_pct or Decimal('0')
        return self.quantita_prodotta_kg * (1 - calo / 100)

    @property
    def costo_unitario_mp(self):
        q = self.quantita_effettiva_kg
        if not q:
            return None
        return self.costo_totale_mp / q

    @property
    def costo_unitario_imballi(self):
        q = self.quantita_prodotta_kg
        if not q:
            return None
        return self.costo_totale_imballi / q

    @property
    def costo_unitario_lavoro(self):
        q = self.quantita_prodotta_kg
        if not q:
            return None
        return self.costo_totale_lavoro / q

    @property
    def totale_costi_per_kg(self):
        parts = [self.costo_unitario_mp, self.costo_unitario_imballi, self.costo_unitario_lavoro]
        return sum(p for p in parts if p is not None)

    @property
    def prezzo_senza_iva(self):
        if not self.prezzo_vendita_iva:
            return None
        iva = self.aliquota_iva or Decimal('0')
        return self.prezzo_vendita_iva / (1 + iva / 100)

    @property
    def prezzo_per_vaschetta(self):
        p = self.prezzo_senza_iva
        if p and self.porzione_media_kg and self.grammatura_media_kg:
            return p * self.grammatura_media_kg
        return None

    @property
    def margine_netto_per_kg(self):
        p = self.prezzo_senza_iva
        if p is None:
            return None
        return p - self.totale_costi_per_kg

    @property
    def margine_pct(self):
        p = self.prezzo_senza_iva
        m = self.margine_netto_per_kg
        if p and m and p != 0:
            return (m / p) * 100
        return None

    @property
    def food_cost_pct(self):
        mp = self.costo_unitario_mp
        p  = self.prezzo_senza_iva
        if mp is None or not p:
            return None
        return (mp / p) * 100


class RicettaIngrediente(models.Model):
    ricetta       = models.ForeignKey(Ricetta, on_delete=models.CASCADE, related_name='ingredienti')
    ordine        = models.PositiveIntegerField(default=0)
    codice        = models.CharField(max_length=50, blank=True)
    descrizione   = models.CharField(max_length=200, blank=True)
    pct_cp_scarto = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    um            = models.CharField(max_length=20, default='kg')
    peso_qta      = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    pa_senza_iva  = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)

    class Meta:
        ordering = ['ordine']

    @property
    def peso_qta_lorda(self):
        if self.peso_qta is None:
            return None
        pct = self.pct_cp_scarto or Decimal('0')
        if pct > 0:
            return self.peso_qta / (1 - pct / 100)
        return self.peso_qta

    @property
    def importo_totale(self):
        lorda = self.peso_qta_lorda
        if lorda is None or self.pa_senza_iva is None:
            return None
        return lorda * self.pa_senza_iva


class RicettaImballo(models.Model):
    ricetta      = models.ForeignKey(Ricetta, on_delete=models.CASCADE, related_name='imballaggi')
    ordine       = models.PositiveIntegerField(default=0)
    codice       = models.CharField(max_length=50, blank=True)
    descrizione  = models.CharField(max_length=200, blank=True)
    um           = models.CharField(max_length=20, default='pz')
    quantita     = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    pa_senza_iva = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)

    class Meta:
        ordering = ['ordine']

    @property
    def importo_totale(self):
        if self.quantita is None or self.pa_senza_iva is None:
            return None
        return self.quantita * self.pa_senza_iva
