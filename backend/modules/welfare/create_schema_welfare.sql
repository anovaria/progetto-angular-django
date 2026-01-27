-- ============================================================
-- SCHEMA WELFARE - Gestione Buoni Welfare Aziendale
-- Database: DjangoIntranet
-- ============================================================
-- 
-- Eseguire in SSMS o con sqlcmd:
--   sqlcmd -S server -d DjangoIntranet -i create_schema_welfare.sql
--
-- ============================================================

USE [DjangoIntranet]
GO

-- Crea lo schema se non esiste
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'welfare')
BEGIN
    EXEC('CREATE SCHEMA welfare')
    PRINT 'Schema [welfare] creato.'
END
ELSE
BEGIN
    PRINT 'Schema [welfare] già esistente.'
END
GO

-- ============================================================
-- TABELLA: ruoli
-- Ruoli utente (Front-Office, Cassa, Contabilità, Admin)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ruoli' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[ruoli] (
        [id]            INT IDENTITY(1,1) PRIMARY KEY,
        [id_ruolo]      INT NOT NULL UNIQUE,
        [descrizione]   NVARCHAR(255) NOT NULL
    );
    PRINT 'Tabella [welfare].[ruoli] creata.'
    
    -- Inserisci ruoli default
    INSERT INTO [welfare].[ruoli] (id_ruolo, descrizione) VALUES
        (1, 'Front-Office'),
        (2, 'Ufficio Cassa'),
        (3, 'Contabilità'),
        (99, 'Administrator');
    PRINT 'Ruoli default inseriti.'
END
GO

-- ============================================================
-- TABELLA: utenti
-- Utenti dell'applicazione con ruolo assegnato
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'utenti' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[utenti] (
        [id]            INT IDENTITY(1,1) PRIMARY KEY,
        [username]      NVARCHAR(255) NOT NULL UNIQUE,
        [ruolo_id]      INT NULL,
        [data_login]    DATETIME NULL,
        [volte]         INT NOT NULL DEFAULT 0,
        CONSTRAINT [FK_utenti_ruolo] FOREIGN KEY ([ruolo_id]) 
            REFERENCES [welfare].[ruoli]([id_ruolo])
    );
    CREATE INDEX [IX_utenti_username] ON [welfare].[utenti]([username]);
    PRINT 'Tabella [welfare].[utenti] creata.'
END
GO

-- ============================================================
-- TABELLA: tagli_buono
-- Valori nominali dei buoni (5, 10, 20, 25, 30, 50 euro)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tagli_buono' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[tagli_buono] (
        [id]                INT IDENTITY(1,1) PRIMARY KEY,
        [valore_nominale]   INT NOT NULL UNIQUE,
        [attivo]            BIT NOT NULL DEFAULT 1
    );
    PRINT 'Tabella [welfare].[tagli_buono] creata.'
    
    -- Inserisci tagli default
    INSERT INTO [welfare].[tagli_buono] (valore_nominale, attivo) VALUES
        (5, 1), (10, 1), (20, 1), (25, 1), (30, 1), (50, 1);
    PRINT 'Tagli default inseriti.'
END
GO

-- ============================================================
-- TABELLA: richieste
-- Tabella principale delle richieste welfare
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'richieste' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[richieste] (
        [id]                    INT IDENTITY(1,1) PRIMARY KEY,
        [data_creazione]        DATETIME NOT NULL,
        [data_importazione]     DATETIME NOT NULL DEFAULT GETDATE(),
        [data_lavorazione]      DATETIME NULL,
        [data_consegna]         DATETIME NULL,
        [num_richiesta]         NVARCHAR(50) NOT NULL UNIQUE,
        [mittente]              NVARCHAR(255) NULL,
        [nome_mittente]         NVARCHAR(255) NULL,
        [nominativo]            NVARCHAR(255) NOT NULL,
        [emettitore]            NVARCHAR(255) NULL,
        [valore_buono]          DECIMAL(10,2) NOT NULL DEFAULT 0,
        [qta_buono]             INT NOT NULL DEFAULT 0,
        [totale_buono]          DECIMAL(10,2) NOT NULL DEFAULT 0,
        [stato]                 NVARCHAR(50) NOT NULL DEFAULT 'PRONTO',
        [utente_preparazione]   NVARCHAR(30) NULL,
        [utente_consegna]       NVARCHAR(30) NULL,
        [controllo]             FLOAT NOT NULL DEFAULT 0
    );
    CREATE INDEX [IX_richieste_num] ON [welfare].[richieste]([num_richiesta]);
    CREATE INDEX [IX_richieste_stato] ON [welfare].[richieste]([stato]);
    CREATE INDEX [IX_richieste_stato_data] ON [welfare].[richieste]([stato], [data_consegna]);
    CREATE INDEX [IX_richieste_nominativo] ON [welfare].[richieste]([nominativo]);
    PRINT 'Tabella [welfare].[richieste] creata.'
END
GO

-- ============================================================
-- TABELLA: dettaglio_buoni
-- Dettaglio tagli per ogni richiesta (es. 4x50€ + 2x25€)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dettaglio_buoni' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[dettaglio_buoni] (
        [id]                INT IDENTITY(1,1) PRIMARY KEY,
        [richiesta_id]      INT NOT NULL,
        [taglio_valore]     INT NOT NULL,
        [quantita]          INT NOT NULL,
        [totale]            DECIMAL(10,2) NOT NULL,
        CONSTRAINT [FK_dettaglio_richiesta] FOREIGN KEY ([richiesta_id]) 
            REFERENCES [welfare].[richieste]([id]) ON DELETE CASCADE,
        CONSTRAINT [FK_dettaglio_taglio] FOREIGN KEY ([taglio_valore]) 
            REFERENCES [welfare].[tagli_buono]([valore_nominale]),
        CONSTRAINT [UQ_dettaglio_richiesta_taglio] UNIQUE ([richiesta_id], [taglio_valore])
    );
    CREATE INDEX [IX_dettaglio_richiesta] ON [welfare].[dettaglio_buoni]([richiesta_id]);
    PRINT 'Tabella [welfare].[dettaglio_buoni] creata.'
END
GO

-- ============================================================
-- TABELLA: richieste_provvisorie
-- Staging area per import email (prima della validazione)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'richieste_provvisorie' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[richieste_provvisorie] (
        [id]                INT IDENTITY(1,1) PRIMARY KEY,
        [data_creazione]    DATETIME NOT NULL,
        [data_importazione] DATETIME NOT NULL DEFAULT GETDATE(),
        [data_lavorazione]  DATETIME NULL,
        [mittente]          NVARCHAR(255) NULL,
        [nome_mittente]     NVARCHAR(255) NULL,
        [nominativo]        NVARCHAR(255) NOT NULL,
        [num_richiesta]     NVARCHAR(50) NOT NULL,
        [valore_buono]      NVARCHAR(255) NULL,
        [qta_buono]         NVARCHAR(255) NULL,
        [totale_buono]      NVARCHAR(255) NULL,
        [stato]             NVARCHAR(255) NULL DEFAULT 'PRONTO',
        [data_consegna]     DATETIME NULL,
        [emettitore]        NVARCHAR(255) NULL,
        [processato]        BIT NOT NULL DEFAULT 0,
        [errore]            NVARCHAR(MAX) NULL
    );
    CREATE INDEX [IX_provvisorie_processato] ON [welfare].[richieste_provvisorie]([processato]);
    PRINT 'Tabella [welfare].[richieste_provvisorie] creata.'
END
GO

-- ============================================================
-- TABELLA: email_importate
-- Log delle email importate (per debug/audit)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'email_importate' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[email_importate] (
        [id]                INT IDENTITY(1,1) PRIMARY KEY,
        [data_creazione]    DATETIME NOT NULL,
        [sender_name]       NVARCHAR(255) NULL,
        [sender_address]    NVARCHAR(255) NULL,
        [destinatario]      NVARCHAR(255) NULL,
        [cc]                NVARCHAR(255) NULL,
        [bcc]               NVARCHAR(255) NULL,
        [ricevuto_il]       DATETIME NOT NULL,
        [oggetto]           NVARCHAR(255) NULL,
        [categorie]         NVARCHAR(255) NULL,
        [html_body]         NVARCHAR(MAX) NULL,
        [elaborata]         BIT NOT NULL DEFAULT 0,
        [richiesta_creata_id] INT NULL,
        CONSTRAINT [FK_email_richiesta] FOREIGN KEY ([richiesta_creata_id]) 
            REFERENCES [welfare].[richieste]([id]) ON DELETE SET NULL
    );
    CREATE INDEX [IX_email_ricevuto] ON [welfare].[email_importate]([ricevuto_il] DESC);
    PRINT 'Tabella [welfare].[email_importate] creata.'
END
GO

-- ============================================================
-- TABELLA: verifica_eudaimon
-- Import da export Excel Eudaimon per riconciliazione
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'verifica_eudaimon' AND schema_id = SCHEMA_ID('welfare'))
BEGIN
    CREATE TABLE [welfare].[verifica_eudaimon] (
        [id]                    INT IDENTITY(1,1) PRIMARY KEY,
        [numero_richiesta]      NVARCHAR(255) NOT NULL,
        [valore_buono]          NVARCHAR(255) NULL,
        [quantita]              FLOAT NULL,
        [importo]               DECIMAL(10,2) NULL,
        [nominativo_dipendente] NVARCHAR(255) NULL,
        [nome_account]          NVARCHAR(255) NULL,
        [stato]                 NVARCHAR(255) NULL,
        [data_ora_apertura]     NVARCHAR(255) NULL,
        [richiesta_corrispondente_id] INT NULL,
        CONSTRAINT [FK_verifica_richiesta] FOREIGN KEY ([richiesta_corrispondente_id]) 
            REFERENCES [welfare].[richieste]([id]) ON DELETE SET NULL
    );
    CREATE INDEX [IX_verifica_num] ON [welfare].[verifica_eudaimon]([numero_richiesta]);
    PRINT 'Tabella [welfare].[verifica_eudaimon] creata.'
END
GO

-- ============================================================
-- RIEPILOGO
-- ============================================================
PRINT ''
PRINT '============================================================'
PRINT 'Schema [welfare] pronto!'
PRINT ''
PRINT 'Tabelle create:'
SELECT TABLE_SCHEMA, TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'welfare'
ORDER BY TABLE_NAME;
GO
