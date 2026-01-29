<#
.SYNOPSIS
    Test connessione Outlook e Database per Import Welfare

.DESCRIPTION
    Verifica:
    - Connessione a Outlook
    - Esistenza cartella Wellfare
    - Esistenza cartella Importati
    - Email presenti da Eudaimon
    - Connessione al database SQL Server
    
    NON modifica nulla, solo lettura!

.EXAMPLE
    .\Test-WelfareConnection.ps1
#>

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "TEST CONNESSIONE WELFARE" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$errors = 0

# ============================================================
# TEST 1: Outlook
# ============================================================
Write-Host "[TEST 1] Connessione Outlook..." -ForegroundColor Yellow

try {
    $outlook = New-Object -ComObject Outlook.Application
    $namespace = $outlook.GetNamespace("MAPI")
    Write-Host "  OK - Outlook connesso" -ForegroundColor Green
    
    # Account info
    $accounts = $namespace.Accounts
    Write-Host "  Account configurati:" -ForegroundColor Gray
    foreach ($acc in $accounts) {
        Write-Host "    - $($acc.SmtpAddress)" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  ERRORE - Outlook non raggiungibile: $_" -ForegroundColor Red
    $errors++
    Write-Host ""
    Write-Host "Assicurati che Outlook sia aperto e configurato." -ForegroundColor Red
    exit 1
}

# ============================================================
# TEST 2: Cartella Posta in arrivo
# ============================================================
Write-Host ""
Write-Host "[TEST 2] Cartella Posta in arrivo..." -ForegroundColor Yellow

try {
    $inbox = $namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
    Write-Host "  OK - Posta in arrivo trovata" -ForegroundColor Green
    Write-Host "  Elementi totali: $($inbox.Items.Count)" -ForegroundColor Gray
}
catch {
    Write-Host "  ERRORE - Posta in arrivo non accessibile: $_" -ForegroundColor Red
    $errors++
}

# ============================================================
# TEST 3: Cartella Wellfare
# ============================================================
Write-Host ""
Write-Host "[TEST 3] Cartella 'Wellfare'..." -ForegroundColor Yellow

$welfareFolder = $null
foreach ($folder in $inbox.Folders) {
    if ($folder.Name -ieq "Wellfare") {
        $welfareFolder = $folder
        break
    }
}

if ($null -ne $welfareFolder) {
    Write-Host "  OK - Cartella 'Wellfare' trovata" -ForegroundColor Green
    Write-Host "  Elementi nella cartella: $($welfareFolder.Items.Count)" -ForegroundColor Gray
}
else {
    Write-Host "  ERRORE - Cartella 'Wellfare' NON trovata!" -ForegroundColor Red
    Write-Host "  Cartelle disponibili in Posta in arrivo:" -ForegroundColor Yellow
    foreach ($folder in $inbox.Folders) {
        Write-Host "    - $($folder.Name)" -ForegroundColor Gray
    }
    $errors++
}

# ============================================================
# TEST 4: Sottocartella Importati
# ============================================================
Write-Host ""
Write-Host "[TEST 4] Sottocartella 'Importati'..." -ForegroundColor Yellow

if ($null -ne $welfareFolder) {
    $importatiFolder = $null
    foreach ($folder in $welfareFolder.Folders) {
        if ($folder.Name -ieq "Importati") {
            $importatiFolder = $folder
            break
        }
    }
    
    if ($null -ne $importatiFolder) {
        Write-Host "  OK - Cartella 'Importati' trovata" -ForegroundColor Green
        Write-Host "  Elementi nella cartella: $($importatiFolder.Items.Count)" -ForegroundColor Gray
    }
    else {
        Write-Host "  ERRORE - Cartella 'Importati' NON trovata!" -ForegroundColor Red
        Write-Host "  Sottocartelle disponibili in Wellfare:" -ForegroundColor Yellow
        foreach ($folder in $welfareFolder.Folders) {
            Write-Host "    - $($folder.Name)" -ForegroundColor Gray
        }
        $errors++
    }
}
else {
    Write-Host "  SKIP - Test saltato (cartella Wellfare non trovata)" -ForegroundColor Yellow
}

# ============================================================
# TEST 5: Email da Eudaimon
# ============================================================
Write-Host ""
Write-Host "[TEST 5] Email da Eudaimon..." -ForegroundColor Yellow

if ($null -ne $welfareFolder) {
    $eudaimonEmails = @()
    foreach ($item in $welfareFolder.Items) {
        try {
            if ($item.Class -eq 43) {  # olMail
                if ($item.SenderEmailAddress -eq "noreply@eudaimon.it") {
                    $eudaimonEmails += $item
                }
            }
        }
        catch { }
    }
    
    Write-Host "  Email totali in Wellfare: $($welfareFolder.Items.Count)" -ForegroundColor Gray
    Write-Host "  Email da noreply@eudaimon.it: $($eudaimonEmails.Count)" -ForegroundColor Gray
    
    if ($eudaimonEmails.Count -gt 0) {
        Write-Host "  OK - Trovate $($eudaimonEmails.Count) email da importare" -ForegroundColor Green
        
        # Mostra prime 3
        Write-Host ""
        Write-Host "  Ultime email (max 3):" -ForegroundColor Yellow
        $count = 0
        foreach ($mail in $eudaimonEmails) {
            if ($count -ge 3) { break }
            Write-Host "    [$($mail.ReceivedTime)] $($mail.Subject)" -ForegroundColor Gray
            $count++
        }
    }
    else {
        Write-Host "  INFO - Nessuna email da Eudaimon da processare" -ForegroundColor Yellow
    }
}
else {
    Write-Host "  SKIP - Test saltato (cartella Wellfare non trovata)" -ForegroundColor Yellow
}

# ============================================================
# TEST 6: Connessione Database
# ============================================================
Write-Host ""
Write-Host "[TEST 6] Connessione Database SQL Server..." -ForegroundColor Yellow

$sqlServer = "srviisnew"
$database = "DjangoIntranet"

try {
    $connStr = "Server=$sqlServer;Database=$database;Integrated Security=True;TrustServerCertificate=True"
    $conn = New-Object System.Data.SqlClient.SqlConnection($connStr)
    $conn.Open()
    Write-Host "  OK - Connesso a $sqlServer\$database" -ForegroundColor Green
    
    # Test query
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "SELECT COUNT(*) FROM welfare.richieste"
    $count = $cmd.ExecuteScalar()
    Write-Host "  Richieste esistenti nel DB: $count" -ForegroundColor Gray
    
    $conn.Close()
}
catch {
    Write-Host "  ERRORE - Database non raggiungibile: $_" -ForegroundColor Red
    $errors++
}

# ============================================================
# RIEPILOGO
# ============================================================
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "RIEPILOGO" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

if ($errors -eq 0) {
    Write-Host ""
    Write-Host "TUTTI I TEST PASSATI!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Puoi procedere con lo script di import:" -ForegroundColor Green
    Write-Host "  .\Import-WelfareEmail.ps1 -DryRun   (simula)" -ForegroundColor White
    Write-Host "  .\Import-WelfareEmail.ps1           (esegue)" -ForegroundColor White
}
else {
    Write-Host ""
    Write-Host "ERRORI TROVATI: $errors" -ForegroundColor Red
    Write-Host ""
    Write-Host "Risolvi gli errori prima di procedere." -ForegroundColor Red
}

Write-Host ""
Write-Host "Premi un tasto per chiudere..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
