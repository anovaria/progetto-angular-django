from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cursori', '0002_stampa_cursori_campi_commerciali'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE [cursori].[stampa_cursori]
                ADD [giac_pdv] nvarchar(20) NOT NULL DEFAULT '',
                    [giac_dep] nvarchar(20) NOT NULL DEFAULT '';
            """,
            reverse_sql="""
            ALTER TABLE [cursori].[stampa_cursori]
                DROP COLUMN [giac_pdv], [giac_dep];
            """,
        ),
    ]
