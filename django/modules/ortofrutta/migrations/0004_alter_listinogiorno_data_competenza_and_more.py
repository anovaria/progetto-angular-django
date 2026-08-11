from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ortofrutta', '0003_alter_listinogiorno_data_competenza'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='listinogiorno',
            name='uniq_listino_giorno_articolo',
        ),
        migrations.AlterField(
            model_name='listinogiorno',
            name='data_competenza',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='scansioneortofrutta',
            name='data_competenza',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='listinogiorno',
            constraint=models.UniqueConstraint(
                fields=('data_competenza', 'codart'),
                name='uniq_listino_giorno_articolo',
            ),
        ),
    ]