from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('piano_promo', '0002_promosessioneriga_piano'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='promosessione',
                    name='query_piani',
                    field=models.CharField(blank=True, max_length=500),
                ),
                migrations.AddField(
                    model_name='promosessione',
                    name='query_data_da',
                    field=models.DateField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='promosessione',
                    name='query_data_a',
                    field=models.DateField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='promosessione',
                    name='query_sett',
                    field=models.CharField(blank=True, max_length=100),
                ),
            ],
            database_operations=[],
        ),
    ]
