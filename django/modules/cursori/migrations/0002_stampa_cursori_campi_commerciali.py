from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cursori', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE [cursori].[stampa_cursori]
                ADD [prezzo_vend] nvarchar(20) NOT NULL DEFAULT '',
                    [ccom]        nvarchar(20)  NOT NULL DEFAULT '',
                    [descrccom]   nvarchar(100) NOT NULL DEFAULT '',
                    [codforn]     nvarchar(20)  NOT NULL DEFAULT '',
                    [descforn]    nvarchar(100) NOT NULL DEFAULT '';
            """,
            reverse_sql="""
            ALTER TABLE [cursori].[stampa_cursori]
                DROP COLUMN [prezzo_vend], [ccom], [descrccom], [codforn], [descforn];
            """,
        ),
    ]
