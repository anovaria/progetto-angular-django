from django.db import migrations


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE [cursori].[lista_inventario] (
                [id]               bigint        IDENTITY(1,1) NOT NULL PRIMARY KEY,
                [numero_richiesta] nvarchar(50)  NOT NULL,
                [cod_articolo]     nvarchar(20)  NOT NULL,
                [descrizione]      nvarchar(200) NOT NULL DEFAULT '',
                [qtar]             nvarchar(30)  NOT NULL DEFAULT '',
                [cd_ean]           nvarchar(20)  NOT NULL DEFAULT '',
                [elab]             nvarchar(2)   NOT NULL DEFAULT '0',
                [tipo_articolo]    nvarchar(30)  NOT NULL DEFAULT '',
                [creato_il]        datetime2     NOT NULL DEFAULT GETDATE()
            );
            CREATE INDEX [ix_listainv_numerorichiesta]
                ON [cursori].[lista_inventario] ([numero_richiesta]);
            """,
            reverse_sql="DROP TABLE IF EXISTS [cursori].[lista_inventario];",
        ),

        migrations.RunSQL(
            sql="""
            CREATE TABLE [cursori].[pos_articoli_glob] (
                [id]               bigint        IDENTITY(1,1) NOT NULL PRIMARY KEY,
                [numero_richiesta] nvarchar(50)  NOT NULL,
                [corsia]           nvarchar(20)  NOT NULL DEFAULT '',
                [campata]          nvarchar(20)  NOT NULL DEFAULT '',
                [cod_articolo]     nvarchar(20)  NOT NULL,
                [descrizione]      nvarchar(200) NOT NULL DEFAULT '',
                [stato]            nvarchar(10)  NOT NULL DEFAULT '',
                [pz_xcrt]          nvarchar(10)  NOT NULL DEFAULT '',
                [ean]              nvarchar(20)  NOT NULL DEFAULT '',
                [qta]              nvarchar(10)  NOT NULL DEFAULT '',
                [mini]             nvarchar(10)  NOT NULL DEFAULT '',
                [max_val]          nvarchar(10)  NOT NULL DEFAULT '',
                [facing]           nvarchar(10)  NOT NULL DEFAULT '',
                [elaborato]        nvarchar(2)   NOT NULL DEFAULT 'N',
                [ip]               nvarchar(40)  NOT NULL DEFAULT '',
                [creato_il]        datetime2     NOT NULL DEFAULT GETDATE(),
                [aggiornato_il]    datetime2     NOT NULL DEFAULT GETDATE()
            );
            CREATE INDEX [ix_posart_numerorichiesta]
                ON [cursori].[pos_articoli_glob] ([numero_richiesta]);
            CREATE INDEX [ix_posart_codart]
                ON [cursori].[pos_articoli_glob] ([cod_articolo]);
            """,
            reverse_sql="DROP TABLE IF EXISTS [cursori].[pos_articoli_glob];",
        ),

        migrations.RunSQL(
            sql="""
            CREATE TABLE [cursori].[stampa_cursori] (
                [id]               bigint        IDENTITY(1,1) NOT NULL PRIMARY KEY,
                [numero_richiesta] nvarchar(50)  NOT NULL,
                [cod_articolo]     nvarchar(20)  NOT NULL,
                [descrizione]      nvarchar(200) NOT NULL DEFAULT '',
                [num_cursori]      int           NOT NULL DEFAULT 1,
                [tipo_cursore]     int           NOT NULL DEFAULT 1,
                [elaborato]        nvarchar(5)   NOT NULL DEFAULT 'NO',
                [ip]               nvarchar(40)  NOT NULL DEFAULT '',
                [bl]               nvarchar(20)  NOT NULL DEFAULT '',
                [creato_il]        datetime2     NOT NULL DEFAULT GETDATE()
            );
            CREATE INDEX [ix_stampacur_numerorichiesta]
                ON [cursori].[stampa_cursori] ([numero_richiesta]);
            """,
            reverse_sql="DROP TABLE IF EXISTS [cursori].[stampa_cursori];",
        ),
    ]
