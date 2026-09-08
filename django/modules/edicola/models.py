from __future__ import annotations

from django.db import models


class EdicolaPrincipale(models.Model):
    """Tabella principale (equivalente a T_EdicolaPrincipale in Access)."""

    # id: autonumber in Access -> BigAutoField

    sett = models.CharField(max_length=50, blank=True, null=True)
    rep = models.CharField(max_length=50, blank=True, null=True)
    srep = models.CharField(max_length=50, blank=True, null=True)

    ccom = models.TextField(blank=True, null=True)
    descc = models.TextField(blank=True, null=True)

    codart = models.BigIntegerField(db_index=True)
    descrart = models.TextField(blank=True, null=True)

    eanprinc = models.IntegerField(blank=True, null=True, db_index=True)
    tipoean = models.IntegerField(blank=True, null=True)
    stato = models.CharField(max_length=50, blank=True, null=True)

    prezzovend = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    giacenza_pdv = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)

    ean = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    dtaini = models.CharField(max_length=50, blank=True, null=True)
    dtafine = models.CharField(max_length=50, blank=True, null=True)
    dtaaggio = models.CharField(max_length=50, blank=True, null=True)

    data = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "edicola_principale"
        indexes = [
            models.Index(fields=["codart", "eanprinc"]),
            models.Index(fields=["ean"]),
        ]

    def __str__(self) -> str:
        return f"{self.codart} - {self.descrart or ''}".strip()


class SalvaPrinc(models.Model):
    """Tabella di backup (equivalente a T_SalvaPrinc in Access)."""

    sett = models.CharField(max_length=50, blank=True, null=True)
    rep = models.CharField(max_length=50, blank=True, null=True)
    srep = models.CharField(max_length=50, blank=True, null=True)

    ccom = models.TextField(blank=True, null=True)
    descc = models.TextField(blank=True, null=True)

    codart = models.BigIntegerField(db_index=True)
    descrart = models.TextField(blank=True, null=True)

    eanprinc = models.IntegerField(blank=True, null=True, db_index=True)
    tipoean = models.IntegerField(blank=True, null=True)
    stato = models.CharField(max_length=50, blank=True, null=True)

    prezzovend = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    giacenza_pdv = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)

    ean = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    dtaini = models.CharField(max_length=50, blank=True, null=True)
    dtafine = models.CharField(max_length=50, blank=True, null=True)
    dtaaggio = models.CharField(max_length=50, blank=True, null=True)

    data = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "edicola_salva_princ"
        indexes = [
            models.Index(fields=["codart"]),
            models.Index(fields=["ean"]),
        ]

    def __str__(self) -> str:
        return f"BKP {self.codart}"


class EdicolaLog(models.Model):
    """Log semplice delle operazioni (utile per replicare la trasparenza di Access)."""

    created_at = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, default="INFO")
    message = models.TextField()
    details = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "edicola_log"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"[{self.level}] {self.created_at:%Y-%m-%d %H:%M:%S} - {self.message[:60]}"
