from django.db import models


class ImportBatch(models.Model):
    filename = models.CharField('Nome file', max_length=255)
    uploaded_at = models.DateTimeField('Caricato il', auto_now_add=True)
    raw_content = models.TextField('Contenuto originale')
    import_dir = models.CharField('Cartella import', max_length=500, blank=True, default='')
    import_saved_name = models.CharField('Nome file salvato', max_length=255, blank=True, default='')

    def __str__(self):
        return f"{self.filename} ({self.uploaded_at:%Y-%m-%d %H:%M})"


class ImportRow(models.Model):
    """
    Un record corrisponde a una riga del file .elab, tipizzata con i campi di dominio.
    L'ID progressivo è la PK automatica di Django.
    """

    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name='rows',
        verbose_name='Import'
    )

    # Numero di riga nel file
    line_number = models.PositiveIntegerField('Numero riga')

    # Riga originale
    raw_line = models.TextField('Riga originale')

    # Campi di dominio
    cod_art_fo = models.CharField('CodArtFo', max_length=50, blank=True)
    descrizione_articolo = models.CharField('Descrizione articolo', max_length=255, blank=True)

    iva = models.IntegerField('IVA', null=True, blank=True)
    prz_acq = models.DecimalField('PrzAcq', max_digits=12, decimal_places=4, null=True, blank=True)
    campo5 = models.DecimalField('Campo5', max_digits=12, decimal_places=4, null=True, blank=True)

    pz_x_crt = models.IntegerField('PzXCrt', null=True, blank=True)
    crt_x_str = models.IntegerField('CrtXstr', null=True, blank=True)
    str_x_plt = models.IntegerField('StrXplt', null=True, blank=True)
    tot_colli = models.IntegerField('TotColli', null=True, blank=True)

    ean = models.CharField('EAN', max_length=32, blank=True)

    class Meta:
        ordering = ['line_number']

    def __str__(self):
        return f"{self.batch.filename} – riga {self.line_number}"


class GoldTableSnapshot(models.Model):
    """Base snapshot row for a Gold table (stored locally in SQLite)."""
    source_table = models.CharField(max_length=128)
    # Raw row as JSON (columns -> values). Useful for fast prototyping without full schema.
    payload = models.JSONField()
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['source_table']),
            models.Index(fields=['synced_at']),
        ]

    def __str__(self):
        return f"{self.source_table} snapshot {self.id}"


class IntermediateAggPrAcq(models.Model):
    """Risultato equivalente a query Access q_AggPrAcqu per uno specifico batch."""
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='q_agg_pracq', verbose_name='Batch')
    dta_aggio = models.CharField(max_length=32, blank=True)
    cod_art_fo = models.CharField(max_length=50, blank=True)
    codart = models.CharField(max_length=50, blank=True)
    descrart = models.CharField(max_length=255, blank=True)
    stato = models.CharField(max_length=32, blank=True)

    cidac_prezzo = models.CharField(max_length=64, blank=True)   # PRACQ da Gold (stringa safe)
    az = models.CharField(max_length=8, blank=True, default='Agg')
    ros_pracq = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    sett = models.CharField(max_length=32, blank=True)
    rep = models.CharField(max_length=32, blank=True)
    srep = models.CharField(max_length=32, blank=True)
    ccom = models.CharField(max_length=32, blank=True)
    descrccom = models.CharField(max_length=255, blank=True)

    ros_iva = models.IntegerField(null=True, blank=True)
    cidac_iva = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['batch', 'cod_art_fo'])]
        ordering = ['rep', 'srep', 'ccom', 'cod_art_fo']


class IntermediateAggiornaEan(models.Model):
    """Equivalente a query Access q_AggiornaEan: EAN presenti nell'elab ma assenti in dbo_t_t_Ean."""
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='q_aggiorna_ean', verbose_name='Batch')
    cod_art_fo = models.CharField(max_length=50, blank=True)
    descrizione_articolo = models.CharField(max_length=255, blank=True)
    ean = models.CharField(max_length=32, blank=True)
    codart = models.CharField(max_length=50, blank=True)  # da dbo_t_Rossetto

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['batch', 'ean']), models.Index(fields=['batch', 'cod_art_fo'])]
        ordering = ['descrizione_articolo', 'cod_art_fo']


class IntermediateAggiornamentiVari(models.Model):
    """Equivalente a query Access q_AggiornamentiVari."""
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='q_agg_var', verbose_name='Batch')
    cod_art_fo = models.CharField(max_length=50, blank=True)
    codart = models.CharField(max_length=50, blank=True)
    descrizione_articolo = models.CharField(max_length=255, blank=True)
    ean = models.CharField(max_length=32, blank=True)

    cidac_pz_x_crt = models.IntegerField(null=True, blank=True)
    agg_pz_x_crt = models.CharField(max_length=8, blank=True)
    r_pz_x_crt = models.IntegerField(null=True, blank=True)

    cidac_crt_x_str = models.IntegerField(null=True, blank=True)  # STRATO
    agg_crt_x_str = models.CharField(max_length=8, blank=True)
    r_crt_x_str = models.IntegerField(null=True, blank=True)

    r_str_x_plt = models.IntegerField(null=True, blank=True)
    cidac_str_x_plt = models.IntegerField(null=True, blank=True)  # PALLET
    agg_str_x_plt = models.CharField(max_length=8, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['batch', 'cod_art_fo'])]
        ordering = ['cod_art_fo']
