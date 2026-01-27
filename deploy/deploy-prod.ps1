#Requires -RunAsAdministrator

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "       DEPLOY COMPLETO - AMBIENTE PROD          " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Configurazione
$FrontendSource = "C:\portale\frontend"
$BackendSource = "C:\portale\backend"
$DestRoot = "C:\inetpub\PortaleIntranet"
$DestAngular = "$DestRoot\angular"
$DestDjango = "$DestRoot\django"
$ServiceName = "DjangoPortalService"
$SiteName = "PortaleIntranet"

# ============================================
# CONFERMA DEPLOY PRODUZIONE
# ============================================
Write-Host "[!!] ATTENZIONE: Stai per deployare in PRODUZIONE!" -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "Digitare 'DEPLOY' per confermare"
if ($confirm -ne "DEPLOY") {
    Write-Host "Deploy annullato." -ForegroundColor Yellow
    exit 0
}
Write-Host ""

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
& .\venv\Scripts\python.exe manage.py collectstatic --noinput --settings=project_core.settings.prod 2>&1 | Out-Null
Pop-Location

if (Test-Path "$DestDjango\staticfiles\admin") {
    Write-Host "   [OK] Static files raccolti" -ForegroundColor Green
}
else {
    Write-Host "   [--] Verifica staticfiles manualmente" -ForegroundColor Yellow
}

# ============================================
# FASE 4: BUILD ANGULAR
# ============================================
Write-Host "[4/6] Build Angular (configurazione prod)..." -ForegroundColor Yellow

Push-Location $FrontendSource

# Esegui build ignorando stderr (warning budget)
$ErrorActionPreference = "Continue"
ng build --configuration=production 2>&1 | Out-Null
$exitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"

# Verifica che i file siano stati generati
if ((Test-Path "$FrontendSource\dist\frontend\browser\index.html") -and ($exitCode -eq 0)) {
    Write-Host "   [OK] Build Angular completata" -ForegroundColor Green
}
else {
    Write-Host "   [ERR] Build Angular fallita!" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# ============================================
# FASE 5: DEPLOY FRONTEND ANGULAR
# ============================================
Write-Host "[5/6] Deploy frontend Angular..." -ForegroundColor Yellow

$webConfigContent = $null
if (Test-Path "$DestAngular\web.config") {
    $webConfigContent = Get-Content "$DestAngular\web.config" -Raw
}

robocopy "$FrontendSource\dist\frontend\browser" $DestAngular /MIR /NFL /NDL /NJH /NJS /NP

if ($webConfigContent) {
    $webConfigContent | Set-Content "$DestAngular\web.config" -Force
    Write-Host "   [OK] web.config ripristinato" -ForegroundColor Green
}
else {
    $webConfig = @'
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="API Proxy" stopProcessing="true">
          <match url="^api/(.*)" />
          <action type="Rewrite" url="http://localhost:8000/api/{R:1}" />
        </rule>
        <rule name="Admin Proxy" stopProcessing="true">
          <match url="^admin/(.*)" />
          <action type="Rewrite" url="http://localhost:8000/admin/{R:1}" />
        </rule>
        <rule name="Dashboard Proxy" stopProcessing="true">
          <match url="^dashboard/(.*)" />
          <action type="Rewrite" url="http://localhost:8000/dashboard/{R:1}" />
        </rule>
        <rule name="Dashboard Root" stopProcessing="true">
          <match url="^dashboard$" />
          <action type="Rewrite" url="http://localhost:8000/dashboard/" />
        </rule>
        <rule name="Rossetto Proxy" stopProcessing="true">
          <match url="^rossetto/(.*)" />
          <action type="Rewrite" url="http://localhost:8000/rossetto/{R:1}" />
        </rule>
        <rule name="Rossetto Root" stopProcessing="true">
          <match url="^rossetto$" />
          <action type="Rewrite" url="http://localhost:8000/rossetto/" />
        </rule>
        <rule name="Angular Routes" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
            <add input="{REQUEST_URI}" pattern="^/static/" negate="true" />
          </conditions>
          <action type="Rewrite" url="/index.html" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
'@
    $webConfig | Set-Content "$DestAngular\web.config" -Force
    Write-Host "   [OK] web.config creato" -ForegroundColor Green
}

Write-Host "   [OK] File frontend copiati" -ForegroundColor Green

# ============================================
# FASE 6: AVVIO SERVIZI
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

iisreset /noforce | Out-Null
Write-Host "   [OK] IIS riavviato" -ForegroundColor Green

# ============================================
# RIEPILOGO
# ============================================
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "       DEPLOY PRODUZIONE COMPLETATO!            " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "URL: https://portale.groscidac.local" -ForegroundColor Cyan
Write-Host ""