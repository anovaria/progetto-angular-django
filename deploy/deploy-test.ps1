#Requires -RunAsAdministrator

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "    DEPLOY DJANGO PURO - AMBIENTE TEST          " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Configurazione
$BackendSource = "C:\portale\django"
$DestRoot = "C:\inetpub\PortaleTest"
$DestAngular = "$DestRoot\angular"
$DestDjango = "$DestRoot\django"
$ServiceName = "Djangoportaltest"
$SiteName = "PortaleTest"

# ============================================
# FASE 1: STOP SERVIZIO DJANGO
# ============================================
Write-Host "[1/6] Stop servizio Django..." -ForegroundColor Yellow

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {
    Stop-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 3
    Write-Host "   [OK] Servizio $ServiceName fermato" -ForegroundColor Green
}
else {
    Write-Host "   [--] Servizio non in esecuzione" -ForegroundColor Yellow
}

# ============================================
# FASE 2: DEPLOY BACKEND DJANGO
# ============================================
Write-Host "[2/6] Deploy backend Django..." -ForegroundColor Yellow

robocopy $BackendSource $DestDjango /MIR /XD venv __pycache__ .git logs staticfiles /XF *.pyc *.log /NFL /NDL /NJH /NJS /NP

if ($LASTEXITCODE -le 7) {
    Write-Host "   [OK] File backend copiati" -ForegroundColor Green
}
else {
    Write-Host "   [ERR] Errore copia backend" -ForegroundColor Red
    exit 1
}

# ============================================
# FASE 3: COLLECTSTATIC DJANGO
# ============================================
Write-Host "[3/6] Collectstatic Django..." -ForegroundColor Yellow

Push-Location $DestDjango
$staticOutput = & .\venv\Scripts\python.exe manage.py collectstatic --noinput --settings=project_core.settings.prod 2>&1
$staticExit = $LASTEXITCODE
Pop-Location

if ($staticExit -eq 0) {
    Write-Host "   [OK] Static files raccolti" -ForegroundColor Green
}
else {
    Write-Host "   [ERR] Collectstatic fallito (exit code $staticExit):" -ForegroundColor Red
    $staticOutput | ForEach-Object { Write-Host "        $_" -ForegroundColor Red }
    exit 1
}

# ============================================
# FASE 4: DEPLOY WEB.CONFIG DJANGO PURO
# (nessun Angular - IIS proxia tutto a Django)
# ============================================
Write-Host "[4/6] Deploy web.config Django puro..." -ForegroundColor Yellow

# Svuota la cartella angular (rimuove eventuali file Angular residui)
if (Test-Path $DestAngular) {
    Get-ChildItem $DestAngular | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
else {
    New-Item -ItemType Directory -Path $DestAngular -Force | Out-Null
}

# web.config che proxia TUTTO a Django (porta 8001), tranne /static/
$webConfig = @'
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="Static Files passthrough" stopProcessing="true">
          <match url="^static/(.*)" />
          <action type="None" />
        </rule>
        <rule name="Django Proxy" stopProcessing="true">
          <match url="^(.*)" />
          <action type="Rewrite" url="http://localhost:8001/{R:1}" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
'@
$webConfig | Set-Content "$DestAngular\web.config" -Force
Write-Host "   [OK] web.config Django puro creato (proxy completo -> :8001)" -ForegroundColor Green

# ============================================
# FASE 6: VERIFICA VIRTUAL DIRECTORY + AVVIO
# ============================================
Write-Host "[6/6] Avvio servizi..." -ForegroundColor Yellow

Import-Module WebAdministration -ErrorAction SilentlyContinue

$vdir = Get-WebVirtualDirectory -Site $SiteName -Name "static" -ErrorAction SilentlyContinue
if (!$vdir) {
    New-WebVirtualDirectory -Site $SiteName -Name "static" -PhysicalPath "$DestDjango\staticfiles" -ErrorAction SilentlyContinue
    Write-Host "   [OK] Virtual directory 'static' creata" -ForegroundColor Green
}
else {
    Write-Host "   [OK] Virtual directory 'static' esiste" -ForegroundColor Green
}

Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service.Status -eq "Running") {
    Write-Host "   [OK] Servizio $ServiceName avviato" -ForegroundColor Green
}
else {
    Write-Host "   [ERR] Servizio $ServiceName non avviato: $($service.Status)" -ForegroundColor Red
}

try {
    Stop-Service W3SVC -Force -ErrorAction Stop
    Start-Sleep -Seconds 2
    Start-Service W3SVC -ErrorAction Stop
    Write-Host "   [OK] IIS riavviato" -ForegroundColor Green
} catch {
    iisreset /restart | Out-Null
    Write-Host "   [OK] IIS riavviato (via iisreset)" -ForegroundColor Green
}

# ============================================
# RIEPILOGO
# ============================================
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "       DEPLOY TEST COMPLETATO!                  " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "URL: https://portale-test.groscidac.local" -ForegroundColor Cyan
Write-Host ""
