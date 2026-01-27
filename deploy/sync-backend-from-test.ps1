#Requires -RunAsAdministrator
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Sync Backend da PortaleTest" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$backupName = "backend_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Write-Host "`nCreating backup..." -ForegroundColor Yellow
Copy-Item "C:\portale\backend" "C:\portale\$backupName" -Recurse -Force
Write-Host "Backup: C:\portale\$backupName" -ForegroundColor Green

Write-Host "`nSyncing files..." -ForegroundColor Yellow
robocopy "C:\inetpub\PortaleTest\django\modules" "C:\portale\backend\modules" /E /XD __pycache__ /XF *.pyc *.pyo /NFL /NDL /NJH /NJS
robocopy "C:\inetpub\PortaleTest\django\project_core" "C:\portale\backend\project_core" /E /XD __pycache__ /XF *.pyc *.pyo /NFL /NDL /NJH /NJS
Copy-Item "C:\inetpub\PortaleTest\django\*.py" "C:\portale\backend\" -Force -ErrorAction SilentlyContinue
Copy-Item "C:\inetpub\PortaleTest\django\*.txt" "C:\portale\backend\" -Force -ErrorAction SilentlyContinue

Write-Host "`n================================" -ForegroundColor Green
Write-Host "Sync completata!" -ForegroundColor Green
Write-Host "Ricordati: pip install -r requirements.txt" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Green