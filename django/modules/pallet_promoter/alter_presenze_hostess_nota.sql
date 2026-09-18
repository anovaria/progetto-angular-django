-- ============================================================
-- FIX: colonna 'nota' troppo corta su shared.presenze_hostess
-- Database: DjangoIntranet (e DjangoIntranet-test)
-- ============================================================
--
-- Errore risolto:
--   String or binary data would be truncated in table
--   'DjangoIntranet.shared.presenze_hostess', column 'nota'.
--
-- Causa: colonna nvarchar(50), ma il campo "Varie" del planning
-- hostess (pallet-promoter) non ha limite lato form, quindi note
-- più lunghe (es. elenchi di più nomi) mandano in errore il save.
--
-- Eseguire in SSMS (o sqlcmd) su ENTRAMBI gli ambienti:
--   sqlcmd -S 172.17.10.52 -d DjangoIntranet -i alter_presenze_hostess_nota.sql
--   sqlcmd -S 172.17.10.52 -d DjangoIntranet-test -i alter_presenze_hostess_nota.sql
--
-- ============================================================

USE [DjangoIntranet]
GO

ALTER TABLE shared.presenze_hostess ALTER COLUMN nota nvarchar(255) NULL;
GO

ALTER TABLE shared.presenze_hostess ALTER COLUMN nota_fornitore nvarchar(255) NULL;
GO

PRINT 'Colonne nota / nota_fornitore di shared.presenze_hostess allargate a nvarchar(255).';
GO
