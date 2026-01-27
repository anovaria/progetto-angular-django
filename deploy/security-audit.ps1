#Requires -RunAsAdministrator

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "       SECURITY AUDIT - PORTALE INTRANET        " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$FrontendPath = "C:\portale\frontend"
$BackendPath = "C:\portale\backend"

$hasVulnerabilities = $false
$hasOutdated = $false

# ============================================
# FASE 1: AUDIT ANGULAR (npm)
# ============================================
Write-Host "[1/4] Audit Angular (npm)..." -ForegroundColor Yellow
Write-Host ""

Push-Location $FrontendPath

$npmAuditRaw = npm audit --json 2>$null
if ($npmAuditRaw) {
    $npmAudit = $npmAuditRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($npmAudit.metadata.vulnerabilities.total -gt 0) {
        $hasVulnerabilities = $true
        Write-Host "   [!!] Vulnerabilita trovate:" -ForegroundColor Red
        Write-Host "        - Critical: $($npmAudit.metadata.vulnerabilities.critical)" -ForegroundColor $(if ($npmAudit.metadata.vulnerabilities.critical -gt 0) { "Red" } else { "Green" })
        Write-Host "        - High:     $($npmAudit.metadata.vulnerabilities.high)" -ForegroundColor $(if ($npmAudit.metadata.vulnerabilities.high -gt 0) { "Red" } else { "Green" })
        Write-Host "        - Moderate: $($npmAudit.metadata.vulnerabilities.moderate)" -ForegroundColor $(if ($npmAudit.metadata.vulnerabilities.moderate -gt 0) { "Yellow" } else { "Green" })
        Write-Host "        - Low:      $($npmAudit.metadata.vulnerabilities.low)" -ForegroundColor Green
        Write-Host ""
    }
    else {
        Write-Host "   [OK] Nessuna vulnerabilita npm" -ForegroundColor Green
        Write-Host ""
    }
}
else {
    Write-Host "   [OK] Nessuna vulnerabilita npm" -ForegroundColor Green
    Write-Host ""
}

Pop-Location

# ============================================
# FASE 2: AUDIT DJANGO (pip-audit)
# ============================================
Write-Host "[2/4] Audit Django (pip-audit)..." -ForegroundColor Yellow
Write-Host ""

Push-Location $BackendPath

$pipAuditExists = & .\venv\Scripts\pip.exe show pip-audit 2>$null
if (!$pipAuditExists) {
    Write-Host "   [--] Installazione pip-audit..." -ForegroundColor Yellow
    & .\venv\Scripts\pip.exe install pip-audit --quiet
}

$pipAuditRaw = & .\venv\Scripts\pip-audit.exe --format=json 2>$null
if ($pipAuditRaw) {
    $pipAuditResult = $pipAuditRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($pipAuditResult.dependencies) {
        $vulnDeps = @($pipAuditResult.dependencies | Where-Object { $_.vulns.Count -gt 0 })
        if ($vulnDeps.Count -gt 0) {
            $hasVulnerabilities = $true
            Write-Host "   [!!] Vulnerabilita trovate in $($vulnDeps.Count) pacchetti:" -ForegroundColor Red
            foreach ($dep in $vulnDeps) {
                Write-Host "        - $($dep.name) $($dep.version)" -ForegroundColor Red
                foreach ($vuln in $dep.vulns) {
                    Write-Host "          $($vuln.id) -> fix: $($vuln.fix_versions -join ', ')" -ForegroundColor Yellow
                }
            }
            Write-Host ""
        }
        else {
            Write-Host "   [OK] Nessuna vulnerabilita pip" -ForegroundColor Green
            Write-Host ""
        }
    }
    else {
        Write-Host "   [OK] Nessuna vulnerabilita pip" -ForegroundColor Green
        Write-Host ""
    }
}
else {
    Write-Host "   [OK] Nessuna vulnerabilita pip" -ForegroundColor Green
    Write-Host ""
}

Pop-Location

# ============================================
# FASE 3: PACCHETTI OUTDATED
# ============================================
Write-Host "[3/4] Controllo pacchetti outdated..." -ForegroundColor Yellow
Write-Host ""

$npmOutdatedCount = 0
$pipOutdatedCount = 0
$pipOutdatedList = @()

# npm outdated
Write-Host "   Angular (npm):" -ForegroundColor Cyan
Push-Location $FrontendPath
$npmOutdatedRaw = npm outdated --json 2>$null
if ($npmOutdatedRaw) {
    $npmOutdated = $npmOutdatedRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($npmOutdated -and $npmOutdated.PSObject.Properties) {
        $npmOutdatedCount = @($npmOutdated.PSObject.Properties).Count
        Write-Host "   [--] $npmOutdatedCount pacchetti da aggiornare" -ForegroundColor Yellow
        $hasOutdated = $true
    }
    else {
        Write-Host "   [OK] Tutti i pacchetti aggiornati" -ForegroundColor Green
    }
}
else {
    Write-Host "   [OK] Tutti i pacchetti aggiornati" -ForegroundColor Green
}
Pop-Location

Write-Host ""

# pip outdated
Write-Host "   Django (pip):" -ForegroundColor Cyan
Push-Location $BackendPath
$pipOutdatedRaw = & .\venv\Scripts\pip.exe list --outdated --format=json 2>$null
if ($pipOutdatedRaw) {
    $pipOutdatedList = $pipOutdatedRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($pipOutdatedList -and $pipOutdatedList.Count -gt 0) {
        $pipOutdatedCount = $pipOutdatedList.Count
        Write-Host "   [--] $pipOutdatedCount pacchetti da aggiornare" -ForegroundColor Yellow
        $hasOutdated = $true
    }
    else {
        Write-Host "   [OK] Tutti i pacchetti aggiornati" -ForegroundColor Green
    }
}
else {
    Write-Host "   [OK] Tutti i pacchetti aggiornati" -ForegroundColor Green
}
Pop-Location

Write-Host ""

# ============================================
# FASE 4: AZIONI
# ============================================
Write-Host "[4/4] Azioni disponibili" -ForegroundColor Yellow
Write-Host ""

if ($hasVulnerabilities -or $hasOutdated) {
    Write-Host "   Opzioni:" -ForegroundColor Cyan
    Write-Host "   [1] Fix vulnerabilita (npm audit fix + pip upgrade)" -ForegroundColor White
    Write-Host "   [2] Aggiorna pacchetti outdated" -ForegroundColor White
    Write-Host "   [3] Esegui tutto (fix + aggiornamenti)" -ForegroundColor White
    Write-Host "   [0] Esci senza modifiche" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Seleziona opzione"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "Applicazione fix vulnerabilita..." -ForegroundColor Cyan
            
            Push-Location $FrontendPath
            Write-Host "   [--] npm audit fix..." -ForegroundColor Yellow
            npm audit fix 2>&1 | Out-Null
            Write-Host "   [OK] npm audit fix completato" -ForegroundColor Green
            Pop-Location
            
            Push-Location $BackendPath
            Write-Host "   [--] pip upgrade django..." -ForegroundColor Yellow
            & .\venv\Scripts\pip.exe install --upgrade django --quiet 2>&1 | Out-Null
            & .\venv\Scripts\pip.exe freeze > requirements.txt
            Write-Host "   [OK] Django aggiornato" -ForegroundColor Green
            Pop-Location
        }
        "2" {
            Write-Host ""
            Write-Host "Aggiornamento pacchetti outdated..." -ForegroundColor Cyan
            
            if ($npmOutdatedCount -gt 0) {
                Push-Location $FrontendPath
                Write-Host "   [--] npm update..." -ForegroundColor Yellow
                npm update 2>&1 | Out-Null
                Write-Host "   [OK] npm update completato" -ForegroundColor Green
                Pop-Location
            }
            
            if ($pipOutdatedCount -gt 0) {
                Push-Location $BackendPath
                Write-Host "   [--] pip upgrade..." -ForegroundColor Yellow
                foreach ($pkg in $pipOutdatedList) {
                    Write-Host "        Aggiorno $($pkg.name)..." -ForegroundColor Gray
                    & .\venv\Scripts\pip.exe install --upgrade $pkg.name --quiet 2>&1 | Out-Null
                }
                & .\venv\Scripts\pip.exe freeze > requirements.txt
                Write-Host "   [OK] pip upgrade completato" -ForegroundColor Green
                Pop-Location
            }
        }
        "3" {
            Write-Host ""
            Write-Host "Esecuzione completa (fix + aggiornamenti)..." -ForegroundColor Cyan
            
            # Fix vulnerabilita
            Push-Location $FrontendPath
            Write-Host "   [--] npm audit fix..." -ForegroundColor Yellow
            npm audit fix 2>&1 | Out-Null
            Write-Host "   [OK] npm audit fix completato" -ForegroundColor Green
            Pop-Location
            
            # npm update
            if ($npmOutdatedCount -gt 0) {
                Push-Location $FrontendPath
                Write-Host "   [--] npm update..." -ForegroundColor Yellow
                npm update 2>&1 | Out-Null
                Write-Host "   [OK] npm update completato" -ForegroundColor Green
                Pop-Location
            }
            
            # pip upgrade all
            Push-Location $BackendPath
            Write-Host "   [--] pip upgrade..." -ForegroundColor Yellow
            if ($pipOutdatedList -and $pipOutdatedList.Count -gt 0) {
                foreach ($pkg in $pipOutdatedList) {
                    Write-Host "        Aggiorno $($pkg.name)..." -ForegroundColor Gray
                    & .\venv\Scripts\pip.exe install --upgrade $pkg.name --quiet 2>&1 | Out-Null
                }
            }
            else {
                & .\venv\Scripts\pip.exe install --upgrade django --quiet 2>&1 | Out-Null
            }
            & .\venv\Scripts\pip.exe freeze > requirements.txt
            Write-Host "   [OK] pip upgrade completato" -ForegroundColor Green
            Pop-Location
        }
        "0" {
            Write-Host ""
            Write-Host "Nessuna modifica applicata." -ForegroundColor Yellow
        }
        default {
            Write-Host ""
            Write-Host "Opzione non valida. Nessuna modifica applicata." -ForegroundColor Yellow
        }
    }
    
    if ($choice -eq "1" -or $choice -eq "2" -or $choice -eq "3") {
        Write-Host ""
        Write-Host "================================================" -ForegroundColor Green
        Write-Host "   AGGIORNAMENTI COMPLETATI                     " -ForegroundColor Green
        Write-Host "================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Esegui deploy per applicare le modifiche:" -ForegroundColor Cyan
        Write-Host "   npm run deploy:test" -ForegroundColor White
        Write-Host "   npm run deploy:prod" -ForegroundColor White
        Write-Host ""
    }
}
else {
    Write-Host "   [OK] Nessuna azione necessaria" -ForegroundColor Green
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "   SISTEMA AGGIORNATO E SICURO                  " -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
}