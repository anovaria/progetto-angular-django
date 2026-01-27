from django.db import models

# Import modelli condivisi da pallet_promoter
from modules.pallet_promoter.models import Agenzia, Fornitore, Buyer, Reparto


class Attivita(models.Model):
    """Tipi di attività merchandiser."""
    id = models.AutoField(primary_key=True)
    descrizione = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'shared.attivita'
        verbose_name = 'Attività'
        verbose_name_plural = 'Attività'

    def __str__(self):
        return self.descrizione


class Utente(models.Model):
    """Referenti interni (utenti aziendali)."""
    id = models.AutoField(primary_key=True)
    cognome = models.CharField(max_length=255, blank=True, null=True)
    nome = models.CharField(max_length=255, blank=True, null=True)
    code_reparto = models.CharField(max_length=5, blank=True, null=True)
    code_sotto_reparto = models.CharField(max_length=5, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    attivo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'shared.utenti'
        verbose_name = 'Utente'
        verbose_name_plural = 'Utenti'

    def __str__(self):
        return f"{self.cognome} {self.nome}".strip() or f"Utente {self.id}"

    @property
    def nominativo(self):
        return f"{self.cognome} {self.nome}".strip()


class Merchandiser(models.Model):
    """Anagrafica merchandiser."""
    id = models.AutoField(primary_key=True)
    cognome = models.CharField(max_length=255)
    nome = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    attivo = models.BooleanField(default=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    modificato_il = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'shared.merchandiser'
        verbose_name = 'Merchandiser'
        verbose_name_plural = 'Merchandiser'
        ordering = ['cognome', 'nome']

    def __str__(self):
        return f"{self.cognome} {self.nome}".strip()

    @property
    def nominativo(self):
        return f"{self.cognome} {self.nome}".strip()


class SottoReparto(models.Model):
    """Sotto-reparti."""
    id = models.AutoField(primary_key=True)
    reparto = models.ForeignKey(Reparto, on_delete=models.CASCADE,
                                db_column='reparto_id',
                                related_name='sotto_reparti')
    codice = models.CharField(max_length=5)
    descrizione = models.CharField(max_length=50)
    attivo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'shared.sotto_reparti'
        verbose_name = 'Sotto Reparto'
        verbose_name_plural = 'Sotto Reparti'

    def __str__(self):
        return f"{self.codice} - {self.descrizione}"


class Slot(models.Model):
    """Slot merchandiser (assegnazione a periodo)."""
    id = models.AutoField(primary_key=True)
    merchandiser = models.ForeignKey(Merchandiser, on_delete=models.CASCADE,
                                     db_column='merchandiser_id',
                                     related_name='slots')
    utente = models.ForeignKey(Utente, on_delete=models.SET_NULL,
                               db_column='utente_id',
                               blank=True, null=True,
                               related_name='slots_gestiti')
    data_inizio = models.DateField()
    data_fine = models.DateField()
    # Giorni lavorativi
    lun = models.BooleanField(default=False)
    mar = models.BooleanField(default=False)
    mer = models.BooleanField(default=False)
    gio = models.BooleanField(default=False)
    ven = models.BooleanField(default=False)
    sab = models.BooleanField(default=False)
    dom = models.BooleanField(default=False)
    # Altri campi
    note = models.TextField(blank=True, null=True)
    documento = models.CharField(max_length=50, blank=True, null=True)
    badge = models.CharField(max_length=10, blank=True, null=True)
    plafond_ore = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creato_il = models.DateTimeField(auto_now_add=True)
    modificato_il = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'shared.slot'
        verbose_name = 'Slot'
        verbose_name_plural = 'Slot'
        ordering = ['-data_inizio']

    def __str__(self):
        return f"{self.merchandiser} ({self.data_inizio} - {self.data_fine})"

    @property
    def giorni_attivi(self):
        """Ritorna stringa con giorni attivi."""
        giorni = []
        if self.lun: giorni.append('Lu')
        if self.mar: giorni.append('Ma')
        if self.mer: giorni.append('Me')
        if self.gio: giorni.append('Gi')
        if self.ven: giorni.append('Ve')
        if self.sab: giorni.append('Sa')
        if self.dom: giorni.append('Do')
        return ' '.join(giorni)


class SlotFornitore(models.Model):
    """Assegnazione fornitore/agenzia/attività a slot."""
    id = models.AutoField(primary_key=True)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE,
                             db_column='slot_id',
                             related_name='fornitori')
    agenzia = models.ForeignKey(Agenzia, on_delete=models.SET_NULL,
                                db_column='agenzia_id',
                                blank=True, null=True,
                                related_name='slot_assegnazioni')
    fornitore_id = models.IntegerField(blank=True, null=True)  # codice fornitore
    sotto_reparto = models.ForeignKey(SottoReparto, on_delete=models.SET_NULL,
                                      db_column='sotto_reparto_id',
                                      blank=True, null=True,
                                      related_name='slot_assegnazioni')
    attivita = models.ForeignKey(Attivita, on_delete=models.SET_NULL,
                                 db_column='attivita_id',
                                 blank=True, null=True,
                                 related_name='slot_assegnazioni')
    buyer = models.ForeignKey(Buyer, on_delete=models.SET_NULL,
                              db_column='buyer_id',
                              blank=True, null=True,
                              related_name='slot_assegnazioni')
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.slot_fornitori'
        verbose_name = 'Slot Fornitore'
        verbose_name_plural = 'Slot Fornitori'

    def __str__(self):
        return f"Slot {self.slot_id} - Fornitore {self.fornitore_id}"

    @property
    def fornitore(self):
        """Recupera oggetto Fornitore."""
        if self.fornitore_id:
            return Fornitore.objects.filter(codice=self.fornitore_id).first()
        return None


class SlotIngressoUscita(models.Model):
    """Timbrature giornaliere."""
    id = models.AutoField(primary_key=True)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE,
                             db_column='slot_id',
                             related_name='ingressi_uscite')
    data = models.DateField()
    ingresso_1 = models.TimeField(blank=True, null=True)
    uscita_1 = models.TimeField(blank=True, null=True)
    ingresso_2 = models.TimeField(blank=True, null=True)
    uscita_2 = models.TimeField(blank=True, null=True)
    ingresso_extra = models.TimeField(blank=True, null=True)
    uscita_extra = models.TimeField(blank=True, null=True)
    forzato = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.slot_ingressi_uscite'
        verbose_name = 'Ingresso/Uscita'
        verbose_name_plural = 'Ingressi/Uscite'
        unique_together = ['slot', 'data']
        ordering = ['data']

    def __str__(self):
        return f"Slot {self.slot_id} - {self.data}"

    @property
    def ore_lavorate(self):
        """Calcola ore totali lavorate nel giorno."""
        from datetime import datetime, timedelta
        ore = timedelta()
        
        if self.ingresso_1 and self.uscita_1:
            dt1 = datetime.combine(self.data, self.uscita_1) - datetime.combine(self.data, self.ingresso_1)
            ore += dt1
        
        if self.ingresso_2 and self.uscita_2:
            dt2 = datetime.combine(self.data, self.uscita_2) - datetime.combine(self.data, self.ingresso_2)
            ore += dt2
        
        if self.ingresso_extra and self.uscita_extra:
            dt3 = datetime.combine(self.data, self.uscita_extra) - datetime.combine(self.data, self.ingresso_extra)
            ore += dt3
        
        return round(ore.total_seconds() / 3600, 2)
