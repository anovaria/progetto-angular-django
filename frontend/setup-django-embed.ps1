# Setup Django Embed Components per Angular
# Esegui dalla root del progetto frontend: C:\portale\frontend

$ErrorActionPreference = "Stop"

Write-Host "=== Setup Django Embed Components ===" -ForegroundColor Cyan

# Verifica di essere nella cartella giusta
if (-not (Test-Path "src\app\features")) {
    Write-Host "ERRORE: Esegui questo script dalla root del frontend (C:\portale\frontend)" -ForegroundColor Red
    exit 1
}

# Crea le cartelle
Write-Host "Creazione cartelle..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "src\app\features\django-embed\pages" -Force | Out-Null

# ============================================
# iframe-wrapper.ts
# ============================================
Write-Host "Creazione iframe-wrapper.ts..." -ForegroundColor Yellow
@'
import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-iframe-wrapper',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './iframe-wrapper.html',
  styleUrls: ['./iframe-wrapper.scss']
})
export class IframeWrapperComponent implements OnInit, OnDestroy {
  /**
   * Path Django da caricare (es. '/dashboard/', '/access-app/')
   * NON includere il dominio, verra costruito automaticamente
   */
  @Input() djangoPath: string = '/';
  
  /**
   * Titolo opzionale per la pagina (mostrato durante caricamento)
   */
  @Input() title: string = 'Caricamento...';
  
  /**
   * Mostra/nascondi spinner di caricamento
   */
  @Input() showLoader: boolean = true;

  iframeUrl: SafeResourceUrl | null = null;
  isLoading: boolean = true;
  hasError: boolean = false;

  constructor(private sanitizer: DomSanitizer) {}

  ngOnInit(): void {
    this.buildIframeUrl();
  }

  ngOnDestroy(): void {
    // Cleanup se necessario
  }

  /**
   * Costruisce l'URL completo per l'iframe basandosi sull'ambiente
   */
  private buildIframeUrl(): void {
    try {
      let baseUrl: string;

      if (environment.production) {
        // Test/Prod: URL relativo (stesso dominio via IIS)
        baseUrl = '';
      } else {
        // Dev: URL assoluto dal apiBase (rimuovi /api)
        baseUrl = environment.apiBase.replace('/api', '');
      }

      const fullUrl = `${baseUrl}${this.djangoPath}`;
      this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(fullUrl);
      
    } catch (error) {
      console.error('Errore costruzione URL iframe:', error);
      this.hasError = true;
      this.isLoading = false;
    }
  }

  /**
   * Gestisce il caricamento completato dell'iframe
   */
  onIframeLoad(): void {
    this.isLoading = false;
  }

  /**
   * Gestisce errori di caricamento
   */
  onIframeError(): void {
    this.isLoading = false;
    this.hasError = true;
  }

  /**
   * Ricarica l'iframe
   */
  reload(): void {
    this.isLoading = true;
    this.hasError = false;
    this.buildIframeUrl();
  }
}
'@ | Set-Content -Path "src\app\features\django-embed\iframe-wrapper.ts" -Encoding UTF8

# ============================================
# iframe-wrapper.html
# ============================================
Write-Host "Creazione iframe-wrapper.html..." -ForegroundColor Yellow
@'
<div class="iframe-container">
  
  <!-- Loader -->
  <div class="loader-overlay" *ngIf="isLoading && showLoader">
    <div class="loader-content">
      <div class="spinner"></div>
      <span class="loader-text">{{ title }}</span>
    </div>
  </div>

  <!-- Error State -->
  <div class="error-overlay" *ngIf="hasError">
    <div class="error-content">
      <span class="error-icon">⚠️</span>
      <span class="error-text">Impossibile caricare il contenuto</span>
      <button class="retry-btn" (click)="reload()">Riprova</button>
    </div>
  </div>

  <!-- Iframe -->
  <iframe 
    *ngIf="iframeUrl && !hasError"
    [src]="iframeUrl"
    (load)="onIframeLoad()"
    (error)="onIframeError()"
    frameborder="0"
    class="django-iframe"
    [class.loading]="isLoading">
  </iframe>

</div>
'@ | Set-Content -Path "src\app\features\django-embed\iframe-wrapper.html" -Encoding UTF8

# ============================================
# iframe-wrapper.scss
# ============================================
Write-Host "Creazione iframe-wrapper.scss..." -ForegroundColor Yellow
@'
.iframe-container {
  position: relative;
  width: 100%;
  height: calc(100vh - 64px);
  min-height: 500px;
  background-color: #fafafa;
}

.django-iframe {
  width: 100%;
  height: 100%;
  border: none;
  transition: opacity 0.3s ease;

  &.loading {
    opacity: 0.3;
  }
}

.loader-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.loader-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e0e0e0;
  border-top-color: #2E5090;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loader-text {
  color: #666;
  font-size: 14px;
  font-weight: 500;
}

.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fff;
  z-index: 10;
}

.error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px;
  text-align: center;
}

.error-icon {
  font-size: 48px;
}

.error-text {
  color: #d32f2f;
  font-size: 16px;
  font-weight: 500;
}

.retry-btn {
  padding: 8px 24px;
  background-color: #2E5090;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: #1a3a6e;
  }
}
'@ | Set-Content -Path "src\app\features\django-embed\iframe-wrapper.scss" -Encoding UTF8

# ============================================
# django-embed.routes.ts
# ============================================
Write-Host "Creazione django-embed.routes.ts..." -ForegroundColor Yellow
@'
import { Routes } from '@angular/router';

export const DJANGO_EMBED_ROUTES: Routes = [
  {
    path: 'dashboard',
    loadComponent: () => 
      import('./pages/dashboard').then(m => m.DashboardPageComponent),
    data: { groups: ['ITD'] }
  },
  {
    path: 'access-app',
    loadComponent: () => 
      import('./pages/access-app').then(m => m.AccessAppPageComponent),
    data: { groups: ['ITD'] }
  }
];
'@ | Set-Content -Path "src\app\features\django-embed\django-embed.routes.ts" -Encoding UTF8

# ============================================
# pages/dashboard.ts
# ============================================
Write-Host "Creazione pages/dashboard.ts..." -ForegroundColor Yellow
@'
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [IframeWrapperComponent],
  template: `
    <app-iframe-wrapper 
      djangoPath="/dashboard/"
      title="Caricamento Dashboard...">
    </app-iframe-wrapper>
  `
})
export class DashboardPageComponent {}
'@ | Set-Content -Path "src\app\features\django-embed\pages\dashboard.ts" -Encoding UTF8

# ============================================
# pages/access-app.ts
# ============================================
Write-Host "Creazione pages/access-app.ts..." -ForegroundColor Yellow
@'
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

/**
 * Pagina per l'app Access portata in Django
 * 
 * TODO: Quando ricevi l'app, aggiorna il djangoPath con l'URL corretto
 */
@Component({
  selector: 'app-access-app-page',
  standalone: true,
  imports: [IframeWrapperComponent],
  template: `
    <app-iframe-wrapper 
      [djangoPath]="djangoPath"
      [title]="title">
    </app-iframe-wrapper>
  `
})
export class AccessAppPageComponent {
  djangoPath: string = '/access-app/';  // <-- AGGIORNA CON URL REALE
  title: string = 'Caricamento Applicazione...';
}
'@ | Set-Content -Path "src\app\features\django-embed\pages\access-app.ts" -Encoding UTF8

# ============================================
# Backup e aggiornamento app.routes.ts
# ============================================
Write-Host "Backup app.routes.ts..." -ForegroundColor Yellow
Copy-Item "src\app\app.routes.ts" "src\app\app.routes.ts.bak" -Force

Write-Host "Aggiornamento app.routes.ts..." -ForegroundColor Yellow
@'
import { Routes } from '@angular/router';
import { MainLayoutComponent } from './layout/main-layout/main-layout';
import { LoginComponent } from './login/login';
import { AuthGuard } from './services/auth.guard';

export const routes: Routes = [
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [AuthGuard],
    data: { groups: ['ITD', 'Vendita'] },
    children: [
      {
        path: 'admin',
        loadChildren: () => import('./features/admin/admin.routes').then(m => m.ADMIN_ROUTES)
      },
      {
        path: 'plu',
        loadChildren: () => import('./features/plu/plu.routes').then(m => m.PLU_ROUTES)
      },
      {
        path: 'django',
        loadChildren: () => import('./features/django-embed/django-embed.routes').then(m => m.DJANGO_EMBED_ROUTES)
      }
    ]
  },
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: '**',
    redirectTo: ''
  }
];
'@ | Set-Content -Path "src\app\app.routes.ts" -Encoding UTF8

# ============================================
# Riepilogo
# ============================================
Write-Host ""
Write-Host "=== SETUP COMPLETATO ===" -ForegroundColor Green
Write-Host ""
Write-Host "File creati:" -ForegroundColor Cyan
Write-Host "  src\app\features\django-embed\iframe-wrapper.ts"
Write-Host "  src\app\features\django-embed\iframe-wrapper.html"
Write-Host "  src\app\features\django-embed\iframe-wrapper.scss"
Write-Host "  src\app\features\django-embed\django-embed.routes.ts"
Write-Host "  src\app\features\django-embed\pages\dashboard.ts"
Write-Host "  src\app\features\django-embed\pages\access-app.ts"
Write-Host "  src\app\app.routes.ts (backup in app.routes.ts.bak)"
Write-Host ""
Write-Host "Route disponibili:" -ForegroundColor Cyan
Write-Host "  /django/dashboard   -> Dashboard Django"
Write-Host "  /django/access-app  -> App Access (placeholder)"
Write-Host ""
Write-Host "Prossimi passi:" -ForegroundColor Yellow
Write-Host "  1. ng serve"
Write-Host "  2. Vai su http://localhost:4200/django/dashboard"
Write-Host "  3. Assicurati che Django giri sulla porta 8002"
Write-Host ""
