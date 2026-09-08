from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Ricetta',
            fields=[
                ('id',                     models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codice_articolo',         models.CharField(blank=True, max_length=50)),
                ('descrizione',             models.CharField(max_length=200)),
                ('categoria',               models.CharField(blank=True, max_length=100)),
                ('difficolta',              models.CharField(blank=True, choices=[('bassa','Bassa'),('media','Media'),('alta','Alta')], default='media', max_length=20)),
                ('ean',                     models.CharField(blank=True, max_length=50)),
                ('tipo_contenitore',        models.CharField(blank=True, max_length=100)),
                ('dimensioni_contenitore',  models.CharField(blank=True, max_length=100)),
                ('grammatura_media_kg',     models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('shelf_life',              models.CharField(blank=True, max_length=200)),
                ('conservabilita',          models.CharField(blank=True, max_length=200)),
                ('kcal',                    models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('protidi',                 models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('lipidi',                  models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('glucidi',                 models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('calo_peso_pct',           models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('quantita_prodotta_kg',    models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('porzione_media_kg',       models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('tempo_produzione_min',    models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('costo_al_minuto',         models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('prezzo_vendita_iva',      models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ('aliquota_iva',            models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('ingredienti_etichetta',   models.TextField(blank=True)),
                ('modalita_preparazione',   models.TextField(blank=True)),
                ('abbinamenti',             models.TextField(blank=True)),
                ('consigli_cottura',        models.TextField(blank=True)),
                ('note',                    models.TextField(blank=True)),
                ('creato_da',               models.CharField(blank=True, max_length=100)),
                ('creato_il',               models.DateTimeField(auto_now_add=True)),
                ('aggiornato_il',           models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Ricetta',
                'verbose_name_plural': 'Ricette',
                'ordering': ['descrizione'],
            },
        ),
        migrations.CreateModel(
            name='RicettaIngrediente',
            fields=[
                ('id',            models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ricetta',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredienti', to='ricette.ricetta')),
                ('ordine',        models.PositiveIntegerField(default=0)),
                ('codice',        models.CharField(blank=True, max_length=50)),
                ('descrizione',   models.CharField(blank=True, max_length=200)),
                ('pct_cp_scarto', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('um',            models.CharField(default='kg', max_length=20)),
                ('peso_qta',      models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('pa_senza_iva',  models.DecimalField(blank=True, decimal_places=5, max_digits=10, null=True)),
            ],
            options={'ordering': ['ordine']},
        ),
        migrations.CreateModel(
            name='RicettaImballo',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ricetta',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='imballaggi', to='ricette.ricetta')),
                ('ordine',       models.PositiveIntegerField(default=0)),
                ('codice',       models.CharField(blank=True, max_length=50)),
                ('descrizione',  models.CharField(blank=True, max_length=200)),
                ('um',           models.CharField(default='pz', max_length=20)),
                ('quantita',     models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('pa_senza_iva', models.DecimalField(blank=True, decimal_places=5, max_digits=10, null=True)),
            ],
            options={'ordering': ['ordine']},
        ),
    ]
