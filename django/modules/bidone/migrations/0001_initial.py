from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='BidoneAnnotazione',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_name', models.CharField(max_length=50)),
                ('record_key', models.CharField(max_length=300)),
                ('gestito', models.BooleanField(default=False)),
                ('nota', models.TextField(blank=True)),
                ('utente', models.CharField(max_length=100)),
                ('aggiornato_il', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'bidone_annotazione',
                'unique_together': {('app_name', 'record_key')},
            },
        ),
    ]
