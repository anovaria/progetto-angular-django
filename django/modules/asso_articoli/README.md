# AssoArticoli - Gestione Assortimenti

Migrazione dell'applicazione MS Access "AssoArticoli" in Django, integrata nel portale Pallet-Promoter.

## 📋 Funzionalità

### Core Features
- **Visualizzazione Articoli**: Ricerca e filtro articoli per CCOM (Codice Commerciale)
- **Barcode EAN13**: Generazione automatica barcode con libreria python-barcode
- **Export Excel**: Export completo con barcode embedded come immagini PNG
- **Report Inventario**: Report articoli con giacenze PDV e Deposito
- **Report Reparti**: Report specializzati per BAR e MACELLERIA

### Dati Source
- **Database**: Db_GoldReport (MSSQL) - Read Only
- **Tabelle**:
  - `dbo.v_MasterAssortimenti` - Dati master articoli
  - `dbo.v_AllArticolo` - Giacenze PDV e Deposito

## 🚀 Installazione

### 1. Copia file nel progetto Django

```bash
# Copia l'app nella directory del progetto
cd C:\inetpub\wwwroot\django_intranet
mkdir asso_articoli

# Copia tutti i file:
# - models.py
# - views.py
# - urls.py
# - apps.py
# - __init__.py
# - barcode_utils.py
# - excel_utils.py
```

### 2. Installa dipendenze Python

```powershell
# Attiva l'ambiente virtuale
cd C:\inetpub\wwwroot\django_intranet
.\venv\Scripts\Activate.ps1

# Installa le nuove dipendenze
pip install python-barcode==0.15.1
pip install openpyxl==3.1.2
pip install Pillow==10.2.0
```

### 3. Configura settings.py

In `django_intranet/settings.py`:

```python
INSTALLED_APPS = [
    # ... altre app
    'asso_articoli',  # <-- Aggiungi questa riga
]

# Database Gold già configurato (verifica sia presente):
DATABASES = {
    'default': {
        # ... config default
    },
    'gold': {
        'ENGINE': 'mssql',
        'NAME': 'Db_GoldReport',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'srviisnew',
        'PORT': '1433',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'Trusted_Connection=Yes'
        }
    }
}
```

### 4. Aggiungi URL routing

In `django_intranet/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... altre urls
    path('app/asso_articoli/', include('asso_articoli.urls')),  # <-- Aggiungi
]
```

### 5. Crea directory templates

```bash
mkdir -p asso_articoli/templates/asso_articoli
```

Copia i file template:
- `main.html`
- `report_inventario.html`
- `report_reparto.html`

### 6. Test in Development

```powershell
# Avvia server di sviluppo
python manage.py runserver 0.0.0.0:8000

# Testa l'app
# http://localhost:8000/app/asso_articoli/
```

### 7. Deploy in Production

```powershell
# Collect static files
python manage.py collectstatic --noinput

# Riavvia il servizio Django
Restart-Service django_intranet_service

# L'app sarà disponibile su:
# https://your-server/app/asso_articoli/
```

## 🔧 Struttura File

```
asso_articoli/
├── __init__.py                 # App config
├── apps.py                     # Django app config
├── models.py                   # Models per viste MSSQL
├── views.py                    # Views principali
├── urls.py                     # URL routing
├── barcode_utils.py            # Utility generazione barcode
├── excel_utils.py              # Utility export Excel
├── templates/
│   └── asso_articoli/
│       ├── main.html           # Maschera principale
│       ├── report_inventario.html
│       └── report_reparto.html
└── static/
    └── asso_articoli/
        └── css/
            └── style.css       # (opzionale)
```

## 📱 Integrazione Angular

### Component Angular per iframe

Crea `assortimenti.component.ts`:

```typescript
import { Component } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-assortimenti',
  template: `
    <div class="iframe-container">
      <iframe [src]="iframeUrl" 
              frameborder="0" 
              style="width: 100%; height: calc(100vh - 60px);">
      </iframe>
    </div>
  `
})
export class AssortimentiComponent {
  iframeUrl: SafeResourceUrl;

  constructor(private sanitizer: DomSanitizer) {
    this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
      '/app/asso_articoli/'
    );
  }
}
```

### Aggiungi al routing Angular

In `app-routing.module.ts`:

```typescript
{
  path: 'assortimenti',
  component: AssortimentiComponent,
  canActivate: [AuthGuard],
  data: { roles: ['Administrator', 'Manager'] }  // Personalizza ruoli
}
```

### Aggiungi al menu

In `sidebar.component.ts`:

```typescript
{
  label: 'Assortimenti',
  icon: 'inventory_2',
  route: '/assortimenti',
  roles: ['Administrator', 'Manager']
}
```

## 🎯 Endpoints API

### Maschera Principale
```
GET /app/asso_articoli/
Parametri: ?ccom=XXX&linea1=1&search=keyword
```

### Export Excel
```
GET /app/asso_articoli/export/excel/
Parametri: stessi della maschera principale
Response: File .xlsx con barcode
```

### Report Inventario
```
GET /app/asso_articoli/report/inventario/
Parametri: ?ccom=XXX&export=excel
```

### Report Reparti
```
GET /app/asso_articoli/report/reparto/bar/
GET /app/asso_articoli/report/reparto/macelleria/
Parametri: ?export=excel
```

### API CCOM List
```
GET /app/asso_articoli/api/ccom/
Parametri: ?q=search_term
Response: JSON list
```

## 🔍 Query Originali Access Mappate

| Query Access | Funzionalità Django |
|--------------|---------------------|
| q_MasterAsso | Model: MasterAssortimenti |
| q_allArticolo | Model: AllArticolo |
| q_estrArtA | view: index() con filtri stato |
| q_estrBar | view: report_reparto('bar') |
| q_estrMace | view: report_reparto('macelleria') |
| q_smMain | view: index() |
| q_rStampaInv | view: report_inventario() |
| Query1-4 | Logica fornprinc in filtri |

## 🎨 Caratteristiche UI

- **Bootstrap 5** per styling
- **Material Icons** per icone
- **Responsive** design
- **Barcode SVG** inline per visualizzazione web
- **Barcode PNG** embedded in Excel export
- **Filtri dinamici** CCOM, ricerca, fornitore principale
- **Badge colorati** per stati e giacenze

## 🐛 Troubleshooting

### Barcode non visualizzati
```python
# Verifica che python-barcode sia installato
pip show python-barcode

# Test generazione barcode
from asso_articoli.barcode_utils import generate_ean13_svg
svg = generate_ean13_svg('123456789012')
print(svg)
```

### Export Excel fallisce
```python
# Verifica dipendenze
pip show openpyxl
pip show Pillow

# Test export manuale
from asso_articoli.excel_utils import export_articoli_excel
buffer = export_articoli_excel([{'codart': 'TEST', ...}])
```

### Database connection error
```python
# Verifica config database Gold
python manage.py dbshell --database=gold

# Test query
from asso_articoli.models import MasterAssortimenti
MasterAssortimenti.objects.using('gold').count()
```

## 📊 Performance

- **Paginazione**: Limitato a 100 articoli per pagina nella maschera principale
- **Export Excel**: Limitato a 500 articoli per export (modificabile in views.py)
- **Cache**: Consider implementare cache per lista CCOM (raramente cambia)
- **Indici**: Le viste MSSQL dovrebbero già avere indici ottimizzati

## 🔐 Sicurezza

- **Authentication**: Gestita da Angular (nessun controllo Django)
- **CSRF**: Exempt per endpoint utilizzati da iframe
- **Database**: Read-only access al database Gold
- **XSS**: Template auto-escape Django attivo

## 📝 Note Migrazione

### Differenze da Access

1. **Barcode**: Usa libreria Python moderna invece di font EAN13.TTF
2. **Query Parametriche**: Filtri via GET params invece di riferimenti a controlli maschera
3. **Report**: HTML/Excel invece di Access Report
4. **Formato Date**: ISO format (YYYY-MM-DD) invece di DD/MM/YYYY

### Funzionalità Non Migrate

- Tabella `tb_Associazione` (45 record) - non utilizzata nelle query/report originali
- Tabella `test` (113 record) - solo per testing

## 🚧 Sviluppi Futuri

- [ ] Implementare paginazione vera (Django Paginator)
- [ ] Cache Redis per lista CCOM
- [ ] Export PDF (oltre a Excel)
- [ ] Grafici giacenze (Chart.js)
- [ ] Storico modifiche assortimenti
- [ ] Notifiche articoli sotto scorta

## 📞 Supporto

Per problemi o domande, contattare il team IT.

---

**Versione**: 1.0  
**Data**: Gennaio 2026  
**Autore**: Migrazione Access → Django
