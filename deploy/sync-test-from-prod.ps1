#Requires -RunAsAdministrator
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Rollback Backend da PortaleIntranet (Prod)" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# 1. Backup di PortaleTest prima del rollback
$backupName = "PortaleTest_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Write-Host "`nCreating backup di PortaleTest..." -ForegroundColor Yellow
Copy-Item "C:\inetpub\PortaleTest\django" "C:\inetpub\$backupName" -Recurse -Force
Write-Host "Backup: C:\inetpub\$backupName" -ForegroundColor Green

# 2. Stop servizio Django Test
Write-Host "`nStopping Djangoportaltest..." -ForegroundColor Yellow
Stop-Service Djangoportaltest -ErrorAction SilentlyContinue

# 3. Sync da PortaleIntranet (prod) a PortaleTest
Write-Host "`nSyncing files da PortaleIntranet a PortaleTest..." -ForegroundColor Yellow
robocopy "C:\inetpub\PortaleIntranet\django\modules" "C:\inetpub\PortaleTest\django\modules" /E /MIR /XD __pycache__ /XF *.pyc *.pyo /NFL /NDL /NJH /NJS
robocopy "C:\inetpub\PortaleIntranet\django\project_core" "C:\inetpub\PortaleTest\django\project_core" /E /MIR /XD __pycache__ /XF *.pyc *.pyo /NFL /NDL /NJH /NJS
Copy-Item "C:\inetpub\PortaleIntranet\django\*.py" "C:\inetpub\PortaleTest\django\" -Force -ErrorAction SilentlyContinue
Copy-Item "C:\inetpub\PortaleIntranet\django\*.txt" "C:\inetpub\PortaleTest\django\" -Force -ErrorAction SilentlyContinue

# 4. Restart servizio
Write-Host "`nStarting Djangoportaltest..." -ForegroundColor Yellow
Start-Service Djangoportaltest

# 5. Verifica
Write-Host "`n================================" -ForegroundColor Green
Write-Host "Rollback completato!" -ForegroundColor Green
Write-Host "Backup salvato in: C:\inetpub\$backupName" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Green
Write-Host "`n================================" -ForegroundColor Green
Write-Host "Sync completata!" -ForegroundColor Green
Write-Host "Ricordati: pip install -r requirements.txt" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Green
# Test
Write-Host "`nTest endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Invoke-WebRequest -Uri "http://localhost:8001/api/auth/" -UseBasicParsing -ErrorAction SilentlyContinue | Select-Object StatusCode