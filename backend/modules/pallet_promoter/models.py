"""
Modelli Django per Pallet-Promoter
Schema: shared (MSSQL)
"""

from django.db import models
from django.utils import timezone


# ============================================
# ANAGRAFICHE
# ============================================

class Agenzia(models.Model):
    """Agenzie che forniscono hostess/promoter."""
    id = models.IntegerField(primary_key=True)
    descrizione = models.CharField(max_length=50)
    nota = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.agenzie'
        verbose_name_plural = "Agenzie"
        ordering = ['descrizione']

    def __str__(self):
        return self.descrizione


class Reparto(models.Model):
    """Reparti del supermercato."""
    id = models.IntegerField(primary_key=True)
    descrizione = models.CharField(max_length=40)

    class Meta:
        managed = False
        db_table = 'shared.reparti'
        verbose_name_plural = "Reparti"
        ordering = ['descrizione']

    def __str__(self):
        return self.descrizione


class Buyer(models.Model):
    """Buyer interni che gestiscono le categorie merceologiche."""
    id = models.IntegerField(primary_key=True)
    nominativo = models.CharField(max_length=50)
    codice_as400 = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.buyer'
        verbose_name_plural = "Buyer"
        ordering = ['nominativo']

    def __str__(self):
        return self.nominativo or f"Buyer {self.id}"


class Fornitore(models.Model):
    """Fornitori che acquistano spazi promozionali."""
    codice = models.IntegerField(primary_key=True, db_column='codice')
    nome = models.CharField(max_length=50, db_column='nome')
    buyer = models.CharField(max_length=16, blank=True, null=True)
    reparto = models.CharField(max_length=13, blank=True, null=True)
    codice_commerciale = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.fornitori'
        verbose_name_plural = "Fornitori"
        ordering = ['nome']

    def __str__(self):
        return f"{self.codice} - {self.nome}"


class Hostess(models.Model):
    """Hostess/Promoter che lavorano in store."""
    id = models.IntegerField(primary_key=True)
    nominativo = models.CharField(max_length=50)
    ruolo = models.CharField(max_length=30, blank=True, null=True)
    nota = models.CharField(max_length=100, blank=True, null=True)
    scadenza_libretto_sanitario = models.DateField(blank=True, null=True)
    attiva = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'shared.hostess'
        verbose_name_plural = "Hostess"
        ordering = ['nominativo']

    def __str__(self):
        return self.nominativo


# ============================================
# SPAZI PROMOZIONALI
# ============================================

class Pallet(models.Model):
    """Spazi pallet nel supermercato."""
    id = models.AutoField(primary_key=True)
    codice = models.CharField(max_length=10, unique=True)
    coord_x = models.IntegerField(default=0)
    coord_y = models.IntegerField(default=0)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT, db_column='buyer_id')
    dimensione = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'shared.pallet'
        verbose_name_plural = "Pallet"
        ordering = ['codice']

    def __str__(self):
        return self.codice


class Testata(models.Model):
    """Testate di gondola (fine/inizio corsia)."""
    id = models.IntegerField(primary_key=True)
    locazione = models.CharField(max_length=50)
    bloccata = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'shared.testate'
        verbose_name_plural = "Testate"
        ordering = ['id']

    def __str__(self):
        return f"{self.id} - {self.locazione}"


class Banco(models.Model):
    """Banchi/postazioni."""
    id = models.IntegerField(primary_key=True)
    descrizione = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'shared.banchi'
        verbose_name_plural = "Banchi"

    def __str__(self):
        return self.descrizione


# ============================================
# PERIODI PROMOZIONALI
# ============================================

class Periodo(models.Model):
    """Periodo promozionale (~2 settimane). Importato da Excel CED."""
    id = models.AutoField(primary_key=True)
    codice = models.CharField(max_length=10, unique=True)
    codice_promozione = models.IntegerField()
    descrizione = models.CharField(max_length=100)
    data_inizio = models.DateField()
    data_fine = models.DateField()
    anno = models.IntegerField()
    num_hostess = models.SmallIntegerField(default=8)

    class Meta:
        managed = False
        db_table = 'shared.periodi'
        verbose_name_plural = "Periodi"
        ordering = ['-data_inizio']

    def __str__(self):
        return f"{self.codice} ({self.data_inizio} - {self.data_fine})"

    @property
    def is_corrente(self):
        """Ritorna True se il periodo è quello attuale."""
        oggi = timezone.now().date()
        return self.data_inizio <= oggi <= self.data_fine


# ============================================
# ASSEGNAZIONI
# ============================================

class AssegnazionePallet(models.Model):
    """Assegnazione di un pallet a un fornitore per un periodo."""
    id = models.AutoField(primary_key=True)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE,
                                db_column='periodo_id',
                                related_name='assegnazioni_pallet')
    pallet = models.ForeignKey(Pallet, on_delete=models.PROTECT,
                               db_column='pallet_id',
                               related_name='assegnazioni')
    fornitore = models.ForeignKey(Fornitore, on_delete=models.PROTECT,
                                  db_column='fornitore_id',
                                  blank=True, null=True,
                                  related_name='assegnazioni_pallet')
    dettaglio = models.CharField(max_length=100, blank=True, null=True)
    nota = models.CharField(max_length=50, blank=True, null=True)
    nota_estesa = models.CharField(max_length=255, blank=True, null=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    modificato_il = models.DateTimeField(auto_now=True)
    modificato_da = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.assegnazioni_pallet'
        verbose_name_plural = "Assegnazioni Pallet"
        unique_together = ['periodo', 'pallet']

    def __str__(self):
        forn = self.fornitore.nome if self.fornitore else "(vuoto)"
        return f"{self.pallet.codice} → {forn}"


class AssegnazioneTestata(models.Model):
    """Assegnazione di una testata a un fornitore per mese/anno."""
    id = models.AutoField(primary_key=True)
    mese = models.SmallIntegerField()
    anno = models.SmallIntegerField()
    testata = models.ForeignKey(Testata, on_delete=models.PROTECT,
                                db_column='testata_id',
                                related_name='assegnazioni')
    fornitore = models.ForeignKey(Fornitore, on_delete=models.PROTECT,
                                  db_column='fornitore_id',
                                  blank=True, null=True,
                                  related_name='assegnazioni_testate')
    nota_testata = models.CharField(max_length=50, blank=True, null=True)
    nota_atelier = models.CharField(max_length=50, blank=True, null=True)
    log = models.TextField(blank=True, null=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    modificato_il = models.DateTimeField(auto_now=True)
    modificato_da = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.assegnazioni_testate'
        verbose_name_plural = "Assegnazioni Testate"
        unique_together = ['mese', 'anno', 'testata']

    def __str__(self):
        forn = self.fornitore.nome if self.fornitore else "(vuoto)"
        return f"{self.testata} → {forn} ({self.mese}/{self.anno})"

    def aggiungi_log(self, azione, utente):
        """Aggiunge una riga al log delle modifiche."""
        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M:%S")
        nuova_riga = f"{timestamp} - {azione} da: {utente} ***\r\n"
        self.log = (self.log or "") + nuova_riga


# ============================================
# GESTIONE HOSTESS
# ============================================

class PianificazioneHostess(models.Model):
    """Pianificazione giornaliera hostess."""
    id = models.AutoField(primary_key=True)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE,
                                db_column='periodo_id',
                                related_name='pianificazioni_hostess')
    giorno = models.DateField()
    slot = models.SmallIntegerField()
    hostess = models.ForeignKey(Hostess, on_delete=models.PROTECT,
                                db_column='hostess_id',
                                blank=True, null=True,
                                related_name='pianificazioni')
    nota = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.pianificazione_hostess'
        verbose_name_plural = "Pianificazioni Hostess"
        unique_together = ['giorno', 'slot']

    def __str__(self):
        host = self.hostess.nominativo if self.hostess else "(vuoto)"
        return f"{self.giorno} slot {self.slot} → {host}"


class PresenzaHostess(models.Model):
    """Registrazione presenze/orari giornalieri."""
    TIPO_CHOICES = [
        ('STD', 'Standard'),
        ('FAB', 'Fabbrica/Fornitore'),
    ]

    id = models.AutoField(primary_key=True)
    giorno = models.DateField()
    slot = models.SmallIntegerField()
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES, default='STD')
    hostess = models.ForeignKey(Hostess, on_delete=models.PROTECT,
                                db_column='hostess_id',
                                blank=True, null=True,
                                related_name='presenze')
    agenzia = models.ForeignKey(Agenzia, on_delete=models.PROTECT,
                                db_column='agenzia_id',
                                blank=True, null=True,
                                related_name='presenze')
    ingresso_mattino = models.TimeField(blank=True, null=True)
    uscita_mattino = models.TimeField(blank=True, null=True)
    ingresso_pomeriggio = models.TimeField(blank=True, null=True)
    uscita_pomeriggio = models.TimeField(blank=True, null=True)
    nota = models.CharField(max_length=50, blank=True, null=True)
    fornitore = models.ForeignKey(Fornitore, on_delete=models.PROTECT,
                                  db_column='fornitore_id',
                                  blank=True, null=True,
                                  related_name='presenze_hostess')
    nota_fornitore = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shared.presenze_hostess'
        verbose_name_plural = "Presenze Hostess"
        unique_together = ['giorno', 'slot']

    def __str__(self):
        host = self.hostess.nominativo if self.hostess else "(vuoto)"
        return f"{self.giorno} slot {self.slot} → {host}"

    @property
    def ore_totali(self):
        """Calcola ore totali lavorate nel giorno."""
        ore = 0
        if self.ingresso_mattino and self.uscita_mattino:
            delta = timezone.datetime.combine(timezone.now().date(), self.uscita_mattino) - \
                    timezone.datetime.combine(timezone.now().date(), self.ingresso_mattino)
            ore += delta.total_seconds() / 3600
        if self.ingresso_pomeriggio and self.uscita_pomeriggio:
            delta = timezone.datetime.combine(timezone.now().date(), self.uscita_pomeriggio) - \
                    timezone.datetime.combine(timezone.now().date(), self.ingresso_pomeriggio)
            ore += delta.total_seconds() / 3600
        return ore


# ============================================
# PERMESSI UTENTI
# ============================================

class UtenteBuyer(models.Model):
    """Mapping utente AD -> buyer (permessi)."""
    id = models.AutoField(primary_key=True)
    username_ad = models.CharField(max_length=100)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE,
                              db_column='buyer_id',
                              related_name='utenti')

    class Meta:
        managed = False
        db_table = 'shared.utenti_buyer'
        verbose_name_plural = "Utenti Buyer"
        unique_together = ['username_ad', 'buyer']

    def __str__(self):
        return f"{self.username_ad} → {self.buyer}"

    @classmethod
    def get_buyer_per_utente(cls, username):
        """Ritorna i buyer associati a un utente AD."""
        return Buyer.objects.filter(utenti__username_ad__iexact=username)

    @classmethod
    def is_admin(cls, username):
        """Ritorna True se l'utente non ha buyer assegnati (vede tutto)."""
        return not cls.objects.filter(username_ad__iexact=username).exists()
