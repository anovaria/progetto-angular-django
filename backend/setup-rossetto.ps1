# Setup Rossetto Placeholder
# Esegui dalla root del backend: C:\portale\backend

$ErrorActionPreference = "Stop"

Write-Host "=== Setup Rossetto Placeholder ===" -ForegroundColor Cyan

# Verifica di essere nella cartella giusta
if (-not (Test-Path "modules")) {
    Write-Host "ERRORE: Esegui questo script dalla root del backend (C:\portale\backend)" -ForegroundColor Red
    exit 1
}

# Crea la cartella del modulo
Write-Host "Creazione cartella modules\rossetto..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "modules\rossetto" -Force | Out-Null

# ============================================
# __init__.py
# ============================================
Write-Host "Creazione __init__.py..." -ForegroundColor Yellow
@'
# modules/rossetto/__init__.py
'@ | Set-Content -Path "modules\rossetto\__init__.py" -Encoding UTF8

# ============================================
# apps.py
# ============================================
Write-Host "Creazione apps.py..." -ForegroundColor Yellow
@'
from django.apps import AppConfig

class RossettoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.rossetto'
    verbose_name = 'Rossetto'
'@ | Set-Content -Path "modules\rossetto\apps.py" -Encoding UTF8

# ============================================
# urls.py
# ============================================
Write-Host "Creazione urls.py..." -ForegroundColor Yellow
@'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.rossetto_home, name='rossetto_home'),
]
'@ | Set-Content -Path "modules\rossetto\urls.py" -Encoding UTF8

# ============================================
# views.py
# ============================================
Write-Host "Creazione views.py..." -ForegroundColor Yellow
@'
from django.http import HttpResponse

def rossetto_home(request):
    """
    Rossetto - Placeholder in attesa dell'applicazione
    Sostituisci con l'app reale quando arriva
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rossetto</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                padding: 48px 64px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 500px;
            }
            .icon {
                font-size: 64px;
                margin-bottom: 16px;
            }
            h1 { 
                color: #2E5090; 
                margin-bottom: 12px;
                font-size: 28px;
            }
            p { 
                color: #666; 
                margin-bottom: 24px;
                font-size: 16px;
                line-height: 1.5;
            }
            .status { 
                display: inline-block;
                padding: 10px 20px;
                background: #fff3e0;
                color: #e65100;
                border-radius: 24px;
                font-size: 14px;
                font-weight: 500;
            }
            .info {
                margin-top: 32px;
                padding-top: 24px;
                border-top: 1px solid #eee;
                color: #999;
                font-size: 13px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">📦</div>
            <h1>Rossetto</h1>
            <p>Questa sezione ospitera l'applicazione Rossetto migrata da Access.</p>
            <span class="status">⏳ In attesa dell'applicazione</span>
            <div class="info">
                L'iframe e la navigazione sono pronti.<br>
                Sostituisci questo placeholder con l'app reale.
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)
'@ | Set-Content -Path "modules\rossetto\views.py" -Encoding UTF8

# ============================================
# Aggiorna project_core/urls.py
# ============================================
Write-Host "Aggiornamento project_core/urls.py..." -ForegroundColor Yellow

# Backup
Copy-Item "project_core\urls.py" "project_core\urls.py.bak" -Force

@'
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('modules.auth.urls')),
    path('api/util/', include('modules.util.urls')),
    path('api/', include('modules.plu.urls')),
    path('api/test/', lambda r: HttpResponse("OK")),
    
    # Embedded apps per iframe in Angular
    path('dashboard/', include('modules.dashboard.urls')),
    path('rossetto/', include('modules.rossetto.urls')),
]
'@ | Set-Content -Path "project_core\urls.py" -Encoding UTF8

# ============================================
# Aggiorna settings (base.py) - INSTALLED_APPS
# ============================================
Write-Host ""
Write-Host "=== ATTENZIONE ===" -ForegroundColor Yellow
Write-Host "Aggiungi manualmente 'modules.rossetto' in INSTALLED_APPS nel file base.py:" -ForegroundColor Yellow
Write-Host ""
Write-Host "INSTALLED_APPS = [" -ForegroundColor Gray
Write-Host "    ..." -ForegroundColor Gray
Write-Host "    'modules.dashboard'," -ForegroundColor Gray
Write-Host "    'modules.rossetto',  # <-- AGGIUNGI QUESTA RIGA" -ForegroundColor Green
Write-Host "]" -ForegroundColor Gray

# ============================================
# Riepilogo
# ============================================
Write-Host ""
Write-Host "=== SETUP COMPLETATO ===" -ForegroundColor Green
Write-Host ""
Write-Host "File creati:" -ForegroundColor Cyan
Write-Host "  modules\rossetto\__init__.py"
Write-Host "  modules\rossetto\apps.py"
Write-Host "  modules\rossetto\urls.py"
Write-Host "  modules\rossetto\views.py"
Write-Host "  project_core\urls.py (backup in urls.py.bak)"
Write-Host ""
Write-Host "Prossimi passi:" -ForegroundColor Yellow
Write-Host "  1. Aggiungi 'modules.rossetto' in INSTALLED_APPS (base.py)"
Write-Host "  2. Riavvia Django"
Write-Host "  3. Testa: http://127.0.0.1:8002/rossetto/"
Write-Host "  4. Testa in Angular: /django/rossetto"
Write-Host ""
