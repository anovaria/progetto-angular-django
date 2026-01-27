from django.db import models

class AppGroup(models.Model):
    name = models.CharField(max_length=150, unique=True)
    active = models.BooleanField(default=True)  # solo gruppi attivi contano per permessi

    class Meta:
        db_table = "dbo.AppGroup"  # schema MSSQL corretto
