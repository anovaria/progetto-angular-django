"""
Modelli Django per la gestione Welfare Aziendale
Porting da MS Access wellfare_.accdb
"""

from django.db import models
from django.utils import timezone


class Ruolo(models.Model):
    """
    Ruoli utente per i permessi dell'applicazione.
    Corrisponde a T_Ruoli in Access.
    """
    FRONT_OFFICE = 1
    UFFICIO_CASSA = 2
    CONTABILITA = 3
    ADMIN = 99
    
    RUOLO_CHOICES = [
        (FRONT_OFFICE, 'Front-Office'),
        (UFFICIO_CASSA, 'Ufficio Cassa'),
        (CONTABILITA, 'Contabilità'),
        (ADMIN, 'Administrator'),
    ]
    
    id_ruolo = models.IntegerField(unique=True, choices=RUOLO_CHOICES)
    descrizione = models.CharField(max_length=255)
    
    class Meta:
        managed = False  # Tabella creata via SQL, non migrations
        db_table = 'welfare.ruoli'  # Schema welfare
        verbose_name = 'Ruolo'
        verbose_name_plural = 'Ruoli'
    
    def __str__(self):
        return self.descrizione


class Utente(models.Model):
    """
    Utenti dell'applicazione con ruolo assegnato.
    Corrisponde a T_Utenti in Access.
    """
    username = models.CharField(max_length=255, unique=True)
    ruolo = models.ForeignKey(
        Ruolo, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='utenti',
        to_field='id_ruolo'
    )
    data_login = models.DateTimeField(null=True, blank=True)
    volte = models.IntegerField(default=0, help_text="Contatore accessi")
    
    class Meta:
        managed = False
        db_table = 'welfare.utenti'
        verbose_name = 'Utente'
        verbose_name_plural = 'Utenti'
    
    def __str__(self):
        return self.username
    
    def registra_accesso(self):
        """Aggiorna data login e incrementa contatore."""
        self.data_login = timezone.now()
        self.volte += 1
        self.save(update_fields=['data_login', 'volte'])


class TaglioBuono(models.Model):
    """
    Valori nominali dei buoni disponibili.
    Corrisponde a T_B_TMP in Access.
    """
    valore_nominale = models.IntegerField(unique=True)
    attivo = models.BooleanField(default=True)
    
    class Meta:
        managed = False
        db_table = 'welfare.tagli_buono'
        verbose_name = 'Taglio Buono'
        verbose_name_plural = 'Tagli Buono'
        ordering = ['valore_nominale']
    
    def __str__(self):
        return f"€ {self.valore_nominale}"


class RichiestaWelfare(models.Model):
    """
    Tabella principale delle richieste welfare.
    Corrisponde a T_Wellfare in Access.
    """
    STATO_PRONTO = 'PRONTO'
    STATO_ELABORATO = 'ELABORATO'
    STATO_CONSEGNATO = 'CONSEGNATO'
    STATO_INEVASO = 'INEVASO'
    
    STATO_CHOICES = [
        (STATO_PRONTO, 'Pronto'),
        (STATO_ELABORATO, 'Elaborato'),
        (STATO_CONSEGNATO, 'Consegnato'),
        (STATO_INEVASO, 'Inevaso'),
    ]
    
    # Dati temporali
    data_creazione = models.DateTimeField(
        help_text="Data/ora ricezione email originale"
    )
    data_importazione = models.DateTimeField(
        auto_now_add=True,
        help_text="Data/ora import nel sistema"
    )
    data_lavorazione = models.DateTimeField(
        null=True, blank=True,
        help_text="Data/ora elaborazione"
    )
    data_consegna = models.DateTimeField(
        null=True, blank=True,
        help_text="Data/ora consegna al cliente"
    )
    
    # Dati richiesta
    num_richiesta = models.CharField(
        max_length=50, 
        unique=True,
        db_index=True,
        help_text="Codice richiesta Eudaimon (es. 00577148)"
    )
    mittente = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Email mittente"
    )
    nome_mittente = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Nome azienda richiedente"
    )
    nominativo = models.CharField(
        max_length=255,
        help_text="Nome dipendente beneficiario"
    )
    emettitore = models.CharField(
        max_length=255, 
        blank=True
    )
    
    # Dati buono
    valore_buono = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Taglio singolo buono (€)"
    )
    qta_buono = models.IntegerField(
        help_text="Quantità buoni richiesti"
    )
    totale_buono = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Importo totale (€)"
    )
    
    # Stato e operatori
    stato = models.CharField(
        max_length=50,
        choices=STATO_CHOICES,
        default=STATO_PRONTO,
        db_index=True
    )
    utente_preparazione = models.CharField(
        max_length=30, 
        blank=True,
        help_text="Username operatore preparazione"
    )
    utente_consegna = models.CharField(
        max_length=30, 
        blank=True,
        help_text="Username operatore consegna"
    )
    
    # Campi di controllo
    controllo = models.FloatField(default=0)
    
    class Meta:
        managed = False
        db_table = 'welfare.richieste'
        verbose_name = 'Richiesta Welfare'
        verbose_name_plural = 'Richieste Welfare'
        ordering = ['-data_creazione']
    
    def __str__(self):
        return f"{self.num_richiesta} - {self.nominativo} (€{self.totale_buono})"
    
    def segna_consegnato(self, utente: str):
        """Marca la richiesta come consegnata."""
        self.stato = self.STATO_CONSEGNATO
        self.data_consegna = timezone.now()
        self.utente_consegna = utente
        self.save()
    
    def segna_elaborato(self, utente: str):
        """Marca la richiesta come in elaborazione."""
        self.stato = self.STATO_ELABORATO
        self.data_lavorazione = timezone.now()
        self.utente_preparazione = utente
        self.save()


class DettaglioBuono(models.Model):
    """
    Dettaglio dei tagli per ogni richiesta.
    Corrisponde a T_BuoniCadeau in Access.
    Permette di specificare la composizione dei buoni 
    (es. 4x€50 + 2x€25 = €250).
    """
    richiesta = models.ForeignKey(
        RichiestaWelfare,
        on_delete=models.CASCADE,
        related_name='dettagli_buoni'
    )
    taglio = models.ForeignKey(
        TaglioBuono,
        on_delete=models.PROTECT,
        to_field='valore_nominale',
        db_column='taglio_valore'
    )
    quantita = models.IntegerField()
    totale = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Quantità × Taglio"
    )
    
    class Meta:
        managed = False
        db_table = 'welfare.dettaglio_buoni'
        verbose_name = 'Dettaglio Buono'
        verbose_name_plural = 'Dettagli Buoni'
    
    def __str__(self):
        return f"{self.quantita}x €{self.taglio.valore_nominale}"
    
    def save(self, *args, **kwargs):
        # Calcola automaticamente il totale
        self.totale = self.quantita * self.taglio.valore_nominale
        super().save(*args, **kwargs)


class RichiestaProvvisoria(models.Model):
    """
    Staging area per import email.
    Corrisponde a T_WellfareProvv in Access.
    I record vengono validati e poi spostati in RichiestaWelfare.
    """
    data_creazione = models.DateTimeField()
    data_importazione = models.DateTimeField(auto_now_add=True)
    data_lavorazione = models.DateTimeField(null=True, blank=True)
    
    mittente = models.CharField(max_length=255, blank=True)
    nome_mittente = models.CharField(max_length=255, blank=True)
    nominativo = models.CharField(max_length=255)
    num_richiesta = models.CharField(max_length=50)
    
    valore_buono = models.CharField(max_length=255, blank=True)
    qta_buono = models.CharField(max_length=255, blank=True)
    totale_buono = models.CharField(max_length=255, blank=True)
    
    stato = models.CharField(max_length=255, default='PRONTO')
    data_consegna = models.DateTimeField(null=True, blank=True)
    emettitore = models.CharField(max_length=255, blank=True)
    
    # Flag per tracciare se è stato processato
    processato = models.BooleanField(default=False)
    errore = models.TextField(blank=True)
    
    class Meta:
        managed = False
        db_table = 'welfare.richieste_provvisorie'
        verbose_name = 'Richiesta Provvisoria'
        verbose_name_plural = 'Richieste Provvisorie'
    
    def __str__(self):
        return f"[PROVV] {self.num_richiesta} - {self.nominativo}"


class EmailImportata(models.Model):
    """
    Log delle email importate.
    Corrisponde a T_Email_importate in Access.
    """
    data_creazione = models.DateTimeField()
    sender_name = models.CharField(max_length=255, blank=True)
    sender_address = models.CharField(max_length=255, blank=True)
    destinatario = models.CharField(max_length=255, blank=True)
    cc = models.CharField(max_length=255, blank=True)
    bcc = models.CharField(max_length=255, blank=True)
    ricevuto_il = models.DateTimeField()
    oggetto = models.CharField(max_length=255, blank=True)
    categorie = models.CharField(max_length=255, blank=True)
    html_body = models.TextField(blank=True)
    
    # Flag per tracciare elaborazione
    elaborata = models.BooleanField(default=False)
    richiesta_creata = models.ForeignKey(
        RichiestaWelfare,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_origine',
        db_column='richiesta_creata_id'
    )
    
    class Meta:
        managed = False
        db_table = 'welfare.email_importate'
        verbose_name = 'Email Importata'
        verbose_name_plural = 'Email Importate'
        ordering = ['-ricevuto_il']
    
    def __str__(self):
        return f"{self.oggetto} ({self.ricevuto_il})"


class VerificaEudaimon(models.Model):
    """
    Import da export Excel Eudaimon per verifica incrociata.
    Corrisponde a VerificaEudaimon in Access.
    """
    numero_richiesta = models.CharField(max_length=255)
    valore_buono = models.CharField(max_length=255, blank=True)
    quantita = models.FloatField(null=True, blank=True)
    importo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    nominativo_dipendente = models.CharField(max_length=255, blank=True)
    nome_account = models.CharField(max_length=255, blank=True)
    stato = models.CharField(max_length=255, blank=True)
    data_ora_apertura = models.CharField(max_length=255, blank=True)
    
    # Flag per matching
    richiesta_corrispondente = models.ForeignKey(
        RichiestaWelfare,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verifiche_eudaimon',
        db_column='richiesta_corrispondente_id'
    )
    
    class Meta:
        managed = False
        db_table = 'welfare.verifica_eudaimon'
        verbose_name = 'Verifica Eudaimon'
        verbose_name_plural = 'Verifiche Eudaimon'
    
    def __str__(self):
        return f"[EUDAIMON] {self.numero_richiesta}"
