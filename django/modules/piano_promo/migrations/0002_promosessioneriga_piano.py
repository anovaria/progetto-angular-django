from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('piano_promo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='promosessioneriga',
            name='cod_piano_gold',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterModelOptions(
            name='promosessioneriga',
            options={'ordering': ['cod_piano_gold', 'desc_forn', 'cod_art']},
        ),
    ]
