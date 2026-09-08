#Requires -RunAsAdministrator

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "       SECURITY AUDIT - PORTALE INTRANET        " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$BackendPath = "C:\portale\django"

# ============================================
# PACCHETTI CRITICI - NON aggiornare mai automaticamente
# Richiedono test manuale per compatibilità
# ============================================
$pacchettoCritici = @('django', 'mssql-django', 'pyodbc', 'djangorestframework', 'asgiref')

$hasVulnerabilities = $false
$hasOutdated = $false
$pipOutdatedList = @()
$pipOutdatedSafe = @()
$pipOutdatedCritici = @()

# ============================================
# FASE 1: AUDIT DJANGO (pip-audit)
# ============================================
Write-Host "[1/3] Audit Django (pip-audit)..." -ForegroundColor Yellow
Write-Host ""

Push-Location $BackendPath

$pipAuditExists = & .\venv\Scripts\python.exe -m pip show pip-audit 2>$null
if (!$pipAuditExists) {
    Write-Host "   [--] Installazione pip-audit..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe -m pip install pip-audit --quiet
}

$pipAuditRaw = & .\venv\Scripts\python.exe -m pip_audit --format=json 2>$null
if ($pipAuditRaw) {
    $pipAuditResult = $pipAuditRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($pipAuditResult.dependencies) {
        $vulnDeps = @($pipAuditResult.dependencies | Where-Object { $_.vulns.Count -gt 0 })
        if ($vulnDeps.Count -gt 0) {
            $hasVulnerabilities = $true
            Write-Host "   [!!] Vulnerabilita trovate in $($vulnDeps.Count) pacchetti:" -ForegroundColor Red
            foreach ($dep in $vulnDeps) {
                $isCritico = $pacchettoCritici -contains $dep.name.ToLower()
                $color = if ($isCritico) { "Magenta" } else { "Red" }
                $tag = if ($isCritico) { " [CRITICO - aggiornare manualmente]" } else { "" }
                Write-Host "        - $($dep.name) $($dep.version)$tag" -ForegroundColor $color
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
# FASE 2: PACCHETTI OUTDATED
# ============================================
Write-Host "[2/3] Controllo pacchetti outdated..." -ForegroundColor Yellow
Write-Host ""

Push-Location $BackendPath
$pipOutdatedRaw = & .\venv\Scripts\python.exe -m pip list --outdated --format=json 2>$null
if ($pipOutdatedRaw) {
    $pipOutdatedList = $pipOutdatedRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($pipOutdatedList -and $pipOutdatedList.Count -gt 0) {
        $hasOutdated = $true

        # Separa critici da sicuri
        foreach ($pkg in $pipOutdatedList) {
            if ($pacchettoCritici -contains $pkg.name.ToLower()) {
                $pipOutdatedCritici += $pkg
            } else {
                $pipOutdatedSafe += $pkg
            }
        }

        if ($pipOutdatedCritici.Count -gt 0) {
            Write-Host "   [!!] PACCHETTI CRITICI - NON aggiornare automaticamente:" -ForegroundColor Magenta
            foreach ($pkg in $pipOutdatedCritici) {
                Write-Host "        - $($pkg.name) $($pkg.version) -> $($pkg.latest_version)  (testare compatibilita prima!)" -ForegroundColor Magenta
            }
            Write-Host ""
        }

        if ($pipOutdatedSafe.Count -gt 0) {
            Write-Host "   [--] $($pipOutdatedSafe.Count) pacchetti aggiornabili automaticamente:" -ForegroundColor Yellow
            foreach ($pkg in $pipOutdatedSafe) {
                Write-Host "        - $($pkg.name) $($pkg.version) -> $($pkg.latest_version)" -ForegroundColor Gray
            }
        }
        else {
            Write-Host "   [OK] Nessun pacchetto non-critico da aggiornare" -ForegroundColor Green
        }
        Write-Host ""
    }
    else {
        Write-Host "   [OK] Tutti i pacchetti aggiornati" -ForegroundColor Green
        Write-Host ""
    }
}
else {
    Write-Host "   [OK] Tutti i pacchetti aggiornati" -ForegroundColor Green
    Write-Host ""
}
Pop-Location

# ============================================
# FASE 3: AZIONI
# ============================================
Write-Host "[3/3] Azioni disponibili" -ForegroundColor Yellow
Write-Host ""

if ($hasVulnerabilities -or $hasOutdated) {
    Write-Host "   Opzioni:" -ForegroundColor Cyan
    Write-Host "   [1] Aggiorna solo pacchetti NON critici ($($pipOutdatedSafe.Count) pacchetti)" -ForegroundColor White
    Write-Host "   [0] Esci senza modifiche" -ForegroundColor White
    if ($pipOutdatedCritici.Count -gt 0) {
        Write-Host ""
        Write-Host "   ATTENZIONE: $($pipOutdatedCritici.Count) pacchetti critici NON verranno aggiornati automaticamente." -ForegroundColor Magenta
        Write-Host "   Aggiornali manualmente dopo aver testato la compatibilita su test." -ForegroundColor Magenta
    }
    Write-Host ""

    $choice = Read-Host "Seleziona opzione"

    switch ($choice) {
        "1" {
            if ($pipOutdatedSafe.Count -eq 0) {
                Write-Host ""
                Write-Host "   Nessun pacchetto non-critico da aggiornare." -ForegroundColor Yellow
            }
            else {
                Write-Host ""
                Write-Host "Aggiornamento pacchetti non critici..." -ForegroundColor Cyan
                Push-Location $BackendPath
                foreach ($pkg in $pipOutdatedSafe) {
                    Write-Host "   [--] Aggiorno $($pkg.name)..." -ForegroundColor Gray
                    & .\venv\Scripts\python.exe -m pip install --upgrade $pkg.name --quiet 2>&1 | Out-Null
                }
                & .\venv\Scripts\python.exe -m pip freeze > requirements.txt
                Write-Host "   [OK] Aggiornamento completato" -ForegroundColor Green
                Pop-Location
            }
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

    if ($choice -eq "1" -and $pipOutdatedSafe.Count -gt 0) {
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

    if ($pipOutdatedCritici.Count -gt 0) {
        Write-Host ""
        Write-Host "================================================" -ForegroundColor Magenta
        Write-Host "   PACCHETTI CRITICI IN ATTESA                  " -ForegroundColor Magenta
        Write-Host "================================================" -ForegroundColor Magenta
        Write-Host ""
        Write-Host "   Aggiornare manualmente dopo test su ambiente test:" -ForegroundColor Magenta
        foreach ($pkg in $pipOutdatedCritici) {
            Write-Host "   pip install $($pkg.name)==$($pkg.latest_version)" -ForegroundColor White
        }
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
