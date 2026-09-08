from django.db import models


class PromoSessione(models.Model):
    piano_gold      = models.CharField(max_length=500)
    inizio_sellout  = models.DateField(null=True, blank=True)
    titolo          = models.CharField(max_length=200, blank=True)
    note            = models.TextField(blank=True)
    creato_da       = models.CharField(max_length=100)
    creato_il       = models.DateTimeField(auto_now_add=True)
    aggiornato_il   = models.DateTimeField(auto_now=True)
    # parametri della query salvata per l'aggiornamento automatico
    query_piani     = models.CharField(max_length=500, blank=True)  # comma-separated
    query_data_da   = models.DateField(null=True, blank=True)
    query_data_a    = models.DateField(null=True, blank=True)
    query_sett      = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-creato_il']
        verbose_name = 'Sessione Promo'
        verbose_name_plural = 'Sessioni Promo'

    def __str__(self):
        return f"{self.piano_gold} — {self.titolo or self.creato_da}"

    @property
    def n_totale(self):
        return self.righe.count()

    @property
    def n_inclusi(self):
        return self.righe.filter(stato='incluso').count()

    @property
    def n_esclusi(self):
        return self.righe.filter(stato='escluso').count()

    @property
    def n_neutri(self):
        return self.righe.filter(stato='neutro').count()


class PromoSessioneRiga(models.Model):
    STATI_RIGA = [
        ('neutro',  'Neutro'),
        ('incluso', 'Ordinato'),
        ('escluso', 'Da Ordinare'),
    ]

    sessione        = models.ForeignKey(PromoSessione, on_delete=models.CASCADE, related_name='righe')
    cod_piano_gold  = models.CharField(max_length=50,  blank=True)
    cod_art         = models.CharField(max_length=50,  blank=True)
    desc_art        = models.CharField(max_length=200, blank=True)
    cod_forn        = models.CharField(max_length=50,  blank=True)
    desc_forn       = models.CharField(max_length=200, blank=True)
    giac_pdv        = models.BigIntegerField(null=True, blank=True)
    giac_dep        = models.BigIntegerField(null=True, blank=True)
    cod_art_expo    = models.CharField(max_length=50,  blank=True)
    desc_expo       = models.CharField(max_length=200, blank=True)
    prezzo_promo    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ordine_in_corso = models.CharField(max_length=100, blank=True)
    data_consegna   = models.DateField(null=True, blank=True)
    stato           = models.CharField(max_length=20, choices=STATI_RIGA, default='neutro')
    nota            = models.CharField(max_length=500, blank=True)
    aggiunta_manuale = models.BooleanField(default=False)

    class Meta:
        ordering = ['cod_piano_gold', 'desc_forn', 'cod_art', 'cod_art_expo']
