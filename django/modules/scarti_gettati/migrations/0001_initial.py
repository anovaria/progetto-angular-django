from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ScartoGiornaliero',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField()),
                ('codice_ean_letto', models.CharField(max_length=30)),
                ('codart', models.IntegerField()),
                ('descrart', models.CharField(max_length=200)),
                ('ean_principale', models.BigIntegerField()),
                ('peso_kg', models.DecimalField(decimal_places=3, max_digits=8)),
                ('utente', models.CharField(max_length=50)),
                ('creato_il', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'scarti_gettati_scarto',
                'ordering': ['-creato_il'],
            },
        ),
    ]
