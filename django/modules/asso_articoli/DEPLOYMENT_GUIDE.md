# 📦 GUIDA DEPLOYMENT - AssoArticoli

## ✅ Checklist Pre-Deployment

- [ ] Backup database Access originale
- [ ] Verifica connessione database Gold (Db_GoldReport)
- [ ] Python environment pronto
- [ ] IIS configurato e funzionante
- [ ] Django Intranet già deployato e funzionante

---

## 🚀 DEPLOYMENT STEP-BY-STEP

### STEP 1: Copia File

```powershell
# 1.1 Naviga alla directory del progetto Django
cd C:\inetpub\wwwroot\django_intranet

# 1.2 Crea directory app
mkdir asso_articoli

# 1.3 Estrai il ZIP asso_articoli_django.zip
# Copia tutti i file da asso_articoli_project/ in asso_articoli/

# Struttura finale:
# C:\inetpub\wwwroot\django_intranet\
# └── asso_articoli\
#     ├── __init__.py
#     ├── apps.py
#     ├── models.py
#     ├── views.py
#     ├── urls.py
#     ├── barcode_utils.py
#     ├── excel_utils.py
#     ├── templates\
#     │   └── asso_articoli\
#     │       ├── main.html
#     │       ├── report_inventario.html
#     │       └── report_reparto.html
#     └── static\
#         └── asso_articoli\  (opzionale per ora)
```

### STEP 2: Crea Directory Templates

```powershell
# Crea directory templates
cd C:\inetpub\wwwroot\django_intranet\asso_articoli
mkdir templates
mkdir templates\asso_articoli

# Sposta i file HTML
move main.html templates\asso_articoli\
move report_inventario.html templates\asso_articoli\
move report_reparto.html templates\asso_articoli\
```

### STEP 3: Installa Dipendenze Python

```powershell
# 3.1 Attiva virtual environment
cd C:\inetpub\wwwroot\django_intranet
.\venv\Scripts\Activate.ps1

# 3.2 Installa nuove librerie
pip install python-barcode==0.15.1
pip install openpyxl==3.1.2
pip install Pillow==10.2.0

# 3.3 Verifica installazione
pip list | Select-String -Pattern "barcode|openpyxl|Pillow"

# Output atteso:
# openpyxl          3.1.2
# Pillow            10.2.0
# python-barcode    0.15.1
```

### STEP 4: Configura Django Settings

```powershell
# Apri settings.py
notepad C:\inetpub\wwwroot\django_intranet\django_intranet\settings.py
```

Aggiungi in `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tue app esistenti
    'pallet_promoter',
    'alloca_hostess',
    'merchandiser',
    'solo_orari',
    'welfare',
    'importelab',
    
    # NUOVA APP
    'asso_articoli',  # <-- AGGIUNGI QUESTA RIGA
]
```

Verifica configurazione database `gold` (dovrebbe già esserci):

```python
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'DjangoIntranet',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'srviisnew',
        'PORT': '',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'Trusted_Connection=Yes'
        }
    },
    'gold': {
        'ENGINE': 'mssql',
        'NAME': 'Db_GoldReport',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'srviisnew',
        'PORT': '',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'Trusted_Connection=Yes'
        }
    }
}
```

### STEP 5: Configura URL Routing

```powershell
# Apri urls.py principale
notepad C:\inetpub\wwwroot\django_intranet\django_intranet\urls.py
```

Aggiungi il path per asso_articoli:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Tue app esistenti
    path('app/pallet_promoter/', include('pallet_promoter.urls')),
    path('app/alloca_hostess/', include('alloca_hostess.urls')),
    path('app/merchandiser/', include('merchandiser.urls')),
    path('app/solo_orari/', include('solo_orari.urls')),
    path('app/welfare/', include('welfare.urls')),
    path('app/importelab/', include('importelab.urls')),
    
    # NUOVA APP
    path('app/asso_articoli/', include('asso_articoli.urls')),  # <-- AGGIUNGI
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### STEP 6: Test in Development

```powershell
# 6.1 Verifica sintassi
cd C:\inetpub\wwwroot\django_intranet
python manage.py check

# Output atteso: "System check identified no issues (0 silenced)."

# 6.2 Test import models
python manage.py shell

# In shell:
>>> from asso_articoli.models import MasterAssortimenti, AllArticolo
>>> MasterAssortimenti.objects.using('gold').count()
# Dovrebbe restituire un numero > 0
>>> exit()

# 6.3 Avvia server di test
python manage.py runserver 0.0.0.0:8000

# 6.4 Apri browser e testa:
# http://localhost:8000/app/asso_articoli/
```

### STEP 7: Collect Static Files

```powershell
# Raccogli static files
cd C:\inetpub\wwwroot\django_intranet
python manage.py collectstatic --noinput

# Output: "X static files copied to '...'"
```

### STEP 8: Deploy in Production (IIS)

```powershell
# 8.1 Stop del servizio Django
Stop-Service django_intranet_service

# 8.2 Attendi qualche secondo
Start-Sleep -Seconds 5

# 8.3 Riavvia il servizio
Start-Service django_intranet_service

# 8.4 Verifica stato servizio
Get-Service django_intranet_service

# Output: Status deve essere "Running"

# 8.5 Verifica log
Get-Content C:\inetpub\wwwroot\django_intranet\logs\django.log -Tail 20
```

### STEP 9: Test in Production

```powershell
# 9.1 Apri browser e naviga a:
# https://your-server.com/app/asso_articoli/

# 9.2 Verifica funzionalità:
# - [ ] Maschera principale carica
# - [ ] Dropdown CCOM popolato
# - [ ] Filtri funzionano
# - [ ] Tabella articoli visualizzata
# - [ ] Barcode visualizzati correttamente
# - [ ] Export Excel funziona
# - [ ] Report inventario accessibile
# - [ ] Report BAR accessibile
# - [ ] Report MACELLERIA accessibile
```

---

## 🔧 INTEGRAZIONE ANGULAR

### STEP 10: Crea Component Angular

Nella tua app Angular (`pallet-promoter`):

```bash
cd C:\path\to\angular\app
ng generate component assortimenti
```

### STEP 11: Configura Component

File: `assortimenti.component.ts`

```typescript
import { Component, OnInit } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-assortimenti',
  standalone: true,
  imports: [],
  template: `
    <div class="iframe-container">
      <iframe 
        [src]="iframeUrl" 
        frameborder="0" 
        style="width: 100%; height: calc(100vh - 60px); border: none;">
      </iframe>
    </div>
  `,
  styles: [`
    .iframe-container {
      width: 100%;
      height: 100%;
      overflow: hidden;
    }
  `]
})
export class AssortimentiComponent implements OnInit {
  iframeUrl: SafeResourceUrl;

  constructor(private sanitizer: DomSanitizer) {
    this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
      '/app/asso_articoli/'
    );
  }

  ngOnInit(): void {
    console.log('Assortimenti component loaded');
  }
}
```

### STEP 12: Aggiungi Route

File: `app.routes.ts` (o `app-routing.module.ts`)

```typescript
import { Routes } from '@angular/router';
import { AssortimentiComponent } from './assortimenti/assortimenti.component';

export const routes: Routes = [
  // ... altre route
  {
    path: 'assortimenti',
    component: AssortimentiComponent,
    // Aggiungi guard se necessario
    // canActivate: [AuthGuard],
    // data: { roles: ['Administrator', 'Manager'] }
  }
];
```

### STEP 13: Aggiungi al Menu Sidebar

File: `sidebar.component.ts` (o equivalente)

```typescript
menuItems = [
  // ... altri items
  {
    label: 'Assortimenti',
    icon: 'inventory_2',
    route: '/assortimenti',
    roles: ['Administrator', 'Manager', 'FrontOffice']  // Personalizza
  }
];
```

### STEP 14: Build e Deploy Angular

```powershell
# Nella directory Angular
cd C:\path\to\angular\app

# Build production
ng build --configuration production

# Copia output in IIS
Copy-Item -Path dist\* -Destination C:\inetpub\wwwroot\angular-app\ -Recurse -Force
```

---

## ✅ VERIFICA POST-DEPLOYMENT

### Checklist Funzionale

- [ ] URL principale accessibile: `https://server/app/asso_articoli/`
- [ ] Dropdown CCOM carica dati da Gold
- [ ] Filtro per CCOM funziona
- [ ] Ricerca articoli funziona
- [ ] Checkbox "Fornitore Principale" filtra correttamente
- [ ] Tabella articoli mostra dati corretti
- [ ] Barcode EAN13 visualizzati correttamente
- [ ] Export Excel scarica file
- [ ] Excel contiene barcode come immagini
- [ ] Report Inventario accessibile
- [ ] Export Excel da Report Inventario funziona
- [ ] Report BAR accessibile e filtra famiglie corrette
- [ ] Report MACELLERIA accessibile
- [ ] Component Angular carica iframe correttamente
- [ ] Menu sidebar mostra voce "Assortimenti"
- [ ] Permessi Angular applicati correttamente

### Test Performance

```powershell
# Test query database
# Tempo risposta dovrebbe essere < 2 secondi

Measure-Command {
    Invoke-WebRequest -Uri "https://server/app/asso_articoli/" -UseDefaultCredentials
}
```

### Verifica Log

```powershell
# Log Django
Get-Content C:\inetpub\wwwroot\django_intranet\logs\django.log -Tail 50

# Log IIS
Get-Content C:\inetpub\logs\LogFiles\W3SVC1\u_ex*.log -Tail 50
```

---

## 🐛 TROUBLESHOOTING

### Problema: "ModuleNotFoundError: No module named 'asso_articoli'"

**Soluzione:**
```powershell
# Verifica che la directory esista
Test-Path C:\inetpub\wwwroot\django_intranet\asso_articoli

# Verifica __init__.py
Test-Path C:\inetpub\wwwroot\django_intranet\asso_articoli\__init__.py

# Riavvia servizio
Restart-Service django_intranet_service
```

### Problema: "No module named 'barcode'"

**Soluzione:**
```powershell
# Attiva venv e reinstalla
cd C:\inetpub\wwwroot\django_intranet
.\venv\Scripts\Activate.ps1
pip install python-barcode==0.15.1 --force-reinstall
Restart-Service django_intranet_service
```

### Problema: Barcode non visualizzati

**Soluzione:**
```powershell
# Test generazione barcode in shell
python manage.py shell

>>> from asso_articoli.barcode_utils import generate_ean13_svg
>>> svg = generate_ean13_svg('123456789012')
>>> print(svg)
# Dovrebbe mostrare SVG XML

# Se fallisce, reinstalla Pillow
pip install Pillow==10.2.0 --force-reinstall
```

### Problema: Database connection error

**Soluzione:**
```powershell
# Test connessione Gold
python manage.py dbshell --database=gold

# Se fallisce, verifica settings.py database config
# Verifica che l'utente IIS (IUSR o application pool identity) 
# abbia permessi di lettura su Db_GoldReport
```

### Problema: Export Excel fallisce

**Soluzione:**
```powershell
# Verifica openpyxl
pip show openpyxl

# Test manuale export
python manage.py shell

>>> from asso_articoli.excel_utils import export_articoli_excel
>>> data = [{'codart': 'TEST', 'descrart': 'Test', 'ean': '1234567890123'}]
>>> buffer = export_articoli_excel(data)
>>> print(len(buffer.getvalue()))
# Dovrebbe restituire numero > 0
```

### Problema: Template not found

**Soluzione:**
```powershell
# Verifica path template
Test-Path C:\inetpub\wwwroot\django_intranet\asso_articoli\templates\asso_articoli\main.html

# Se mancano, ricopia da ZIP
```

---

## 📊 MONITORING

### Metriche da Monitorare

1. **Tempo risposta** pagina principale: < 2 secondi
2. **Tempo export Excel**: < 5 secondi (per 100-500 articoli)
3. **Query database**: < 1 secondo
4. **Uso memoria**: monitorare in Task Manager

### Log da Controllare

```powershell
# Log Django (errori app)
Get-Content C:\inetpub\wwwroot\django_intranet\logs\django.log -Tail 100

# Log IIS (errori server)
Get-Content C:\inetpub\logs\LogFiles\W3SVC1\u_ex$(Get-Date -Format yyMMdd).log -Tail 100

# Log Windows Event (errori sistema)
Get-EventLog -LogName Application -Source "Django*" -Newest 50
```

---

## 🔐 SICUREZZA

### Permessi File System

```powershell
# Verifica permessi directory asso_articoli
icacls C:\inetpub\wwwroot\django_intranet\asso_articoli

# L'application pool identity deve avere Read & Execute
```

### Database Security

- ✅ Database Gold configurato come **READ-ONLY**
- ✅ Nessuna operazione di scrittura nel codice
- ✅ Queries utilizzano `.using('gold')` esplicitamente

### Web Security

- ✅ Django auto-escape attivo nei template
- ✅ CSRF protection (gestito da Angular)
- ✅ SQL injection protection (Django ORM)
- ✅ XSS protection (template engine)

---

## 📞 SUPPORTO

In caso di problemi:

1. Verifica log Django
2. Verifica log IIS
3. Test connessione database Gold
4. Verifica permessi file system
5. Contatta team IT con screenshot errori

---

**Ultima revisione**: Gennaio 2026  
**Versione deployment**: 1.0  
**Testato su**: Windows Server 2019/2022, IIS 10, Python 3.11, Django 5.2
