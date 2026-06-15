from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cursori', '0003_stampa_cursori_giacenze'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE [cursori].[stampa_cursori]
                ADD [ean]      nvarchar(20)  NOT NULL DEFAULT '',
                    [codartfo] nvarchar(30)  NOT NULL DEFAULT '';
            """,
            reverse_sql="""
            ALTER TABLE [cursori].[stampa_cursori]
                DROP COLUMN [ean], [codartfo];
            """,
        ),
    ]
