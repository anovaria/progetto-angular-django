from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("importelab", "0002_intermediate_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="importbatch",
            name="import_dir",
            field=models.CharField(blank=True, default="", max_length=500, verbose_name="Cartella import"),
        ),
        migrations.AddField(
            model_name="importbatch",
            name="import_saved_name",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Nome file salvato"),
        ),
    ]
