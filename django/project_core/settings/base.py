from pathlib import Path
from datetime import timedelta
import os

#print(f"--- [DEBUG] INIZIO ESECUZIONE BASE.PY da: {__file__} ---")

# Definizioni di base
SETTINGS_DIR = Path(__file__).resolve().parent
LANGUAGE_CODE = 'it-IT'  # Cambia da 'en-us' a 'it-IT'
TIME_ZONE = 'Europe/Rome'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# 2. Definisce la cartella 'project_core'
PROJECT_CORE_DIR = SETTINGS_DIR.parent

# 3. Definisce la RADICE del progetto
PROJECT_ROOT = PROJECT_CORE_DIR.parent
BASE_DIR = PROJECT_ROOT

# =========================================================================
#  MODIFICHE CHIAVE PER LA SICUREZZA
# =========================================================================

# 1. SECRET_KEY: Viene letta dall'ambiente.
#    Il valore hardcoded (default Django) è usato solo se non specificato.
#    QUESTO VALORE DEVE ESSERE SOVRASCRITTO OBBLIGATORIAMENTE IN PROD.PY
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' # << Fallback INSICURO, solo per sviluppo iniziale
)

# 2. LDAP Configuration: Leggi le configurazioni LDAP dall'ambiente.
#    Questo permette di specificare indirizzi diversi in prod.py.
LDAP_SERVER = os.environ.get("LDAP_SERVER", "SRVDC1.groscidac.local")
LDAP_DOMAIN = os.environ.get("LDAP_DOMAIN", "GROSCIDAC")

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-auth-user',  # ← aggiungi questo
]
# HOSTS consentiti (Solo per sviluppo/default, da sovrascrivere in prod.py)
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Applicazioni
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'rest_framework',
    'corsheaders',
    'project_core',
    'modules.auth.apps.ModulesAuthConfig',
    'modules.util',
    'modules.importelab',
    'modules.edicola',
    'modules.pallet_promoter',
    'modules.alloca_hostess',
    'modules.merchandiser',
    'modules.welfare',
    'modules.asso_articoli',
    'modules.scaricopromo',
    'modules.active_users',
    'modules.stampaoffertefuture.apps.StampaOfferteFutureConfig',
    'modules.portal',
    'modules.plu_web',
    'modules.caricopromo_reparto',
    'modules.masterdata',
    'modules.masterdatacategory',
    'modules.caricopromo_abbig',
    'modules.assortimento_abbig',
    'modules.invenduti',
    'modules.master_ordini',
    'modules.cursori.apps.CursoriConfig',
    'modules.stock_picking.apps.StockPickingConfig',
    'modules.picking_negativi.apps.PickingNegativiConfig',
    'modules.piano_promo.apps.PianoPromoConfig',
    'modules.rio_fornitori.apps.RioFornitoriConfig',
    'modules.rio_fornitori_new.apps.RioFornitoriNewConfig',
    'modules.ricette.apps.RicetteConfig',
    'modules.scarti_gettati.apps.ScartiGettatiConfig',
    'modules.riordino_pdv.apps.RiordinoPdvConfig',
]

# Middleware (Nessun cambiamento)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', # Spostato in cima per sicurezza (base.py)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'modules.portal.middleware.PortalUserMiddleware',
    'modules.portal.middleware.PortalAuthMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'modules.active_users.middleware.ActiveUserMiddleware',
]

# Autenticazione / REST Framework (Nessun cambiamento)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.RemoteUserBackend',
    'django.contrib.auth.backends.ModelBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# URL Configuration
ROOT_URLCONF = 'project_core.urls' # <--- ASSICURATI CHE QUESTA RIGA CI SIA!

# WSGI Application
WSGI_APPLICATION = 'project_core.wsgi.application'

# JWT (Simple JWT) (Nessun cambiamento necessario qui, usa la SECRET_KEY definita sopra)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    # Usa la SECRET_KEY del progetto (che ora è letta dall'ambiente)
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# Logging (Nessun cambiamento)
LOG_DIR = PROJECT_ROOT / 'logs'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{asctime} [{levelname}] {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(PROJECT_ROOT / 'logs' / 'django.log'),
            'maxBytes': 5*1024*1024,
            'backupCount': 3,
            'formatter': 'verbose',
        },
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'loggers': {
        'PIL': {'handlers': ['file', 'console'], 'level': 'WARNING', 'propagate': False},
    },
    'root': {'handlers': ['file', 'console'], 'level': 'DEBUG'},
}

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.environ.get('DB_DEFAULT_NAME', 'DjangoIntranet'),
        'USER': os.environ.get('DB_DEFAULT_USER', 'dev_django_user'),
        'PASSWORD': os.environ.get('DB_DEFAULT_PASSWORD'),
        'HOST': os.environ.get('DB_DEFAULT_HOST', 'localhost\\SQLEXPRESS'),
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
    'goldreport': {
        'ENGINE': 'mssql',
        'NAME': os.environ.get('DB_GOLD_NAME', 'Db_GoldReport'),
        'USER': os.environ.get('DB_GOLD_USER', 'dev_django_user'),
        'PASSWORD': os.environ.get('DB_GOLD_PASSWORD'),
        'HOST': os.environ.get('DB_GOLD_HOST', 'localhost\\SQLEXPRESS'),
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
    'category': {
        'ENGINE': 'mssql',
        'NAME': os.environ.get('DB_CATEGORY_NAME', 'Db_Category'),
        'USER': os.environ.get('DB_GOLD_USER', 'dev_django_user'),
        'PASSWORD': os.environ.get('DB_GOLD_PASSWORD'),
        'HOST': os.environ.get('DB_GOLD_HOST', 'localhost\\SQLEXPRESS'),
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
}
# Nome stampante Windows per stampa frontalini cursori.
# Impostare con il nome esatto come appare in "Dispositivi e stampanti" sul server IIS.
# Es: 'HP LaserJet Pro M501dn' oppure r'\\SRV\NomeStampante'
CURSORI_PRINTER_NAME = 'Kyocera TASKalfa MZ2501ci (7)'
#CURSORI_PRINTER_NAME = 'Microsoft Print to PDF'

# Posizione articoli (riordino PDV): se True, pos_salva NON scrive su t_posArticoli
# (produzione su srviis via linked server), logga soltanto. Default ON per sicurezza.
# Per la scrittura reale: impostare CURSORI_POS_DRY_RUN=0 nell'ambiente (NSSM) e riavviare.
CURSORI_POS_DRY_RUN = os.environ.get('CURSORI_POS_DRY_RUN', '1') != '0'

# Posizione articoli: visibilità della funzione. Default OFF (nascosta): il bottone
# nel menu palmare sparisce e le URL posizione/ e posizione/vedi/ rispondono con un
# redirect alla home. Va abilitata SOLO dove serve impostando CURSORI_POS_ENABLED=1
# nell'ambiente (NSSM) e riavviando. In produzione resta spenta finché non sarà
# pronto il nuovo riordino (il vecchio non si usa più).
CURSORI_POS_ENABLED = os.environ.get('CURSORI_POS_ENABLED', '0') == '1'

# Parametri Rio (modulo riordino_pdv): visibilità della voce di menu e della pagina.
# Default OFF (nascosta): la voce sparisce dal menu e la URL /app/parametri-rio/
# reindirizza alla home. Riguarda il vecchio riordino automatico PDV, che non si usa
# più; resta spenta in produzione finché non sarà pronto il nuovo riordino. Abilitare
# con RIO_PDV_ENABLED=1 nell'ambiente (NSSM) dove serve, poi riavviare.
RIO_PDV_ENABLED = os.environ.get('RIO_PDV_ENABLED', '0') == '1'

# Giacenze LIVE da Oracle GOLDPROD per la Posizione Articoli (come il vecchio web
# service DettaglioArticolo). Stesso account/host Oracle di rio_fornitori_new
# (GOLDCEN su Srvoracle.groscidac.local): testato in dev, ritorna i valori del
# vecchio app (es. 299866 -> 175/13). DSN e password ereditano dai RIO_DASH_ORACLE_*
# se non impostati esplicitamente. Senza password -> giacenze Oracle disattivate e
# si usano i valori ETL (Db_GoldReport) come fallback.
# NB: l'host storico 172.17.10.40 rifiuta GOLDCEN (istanza diversa) -> usare Srvoracle.
CURSORI_ORACLE_DSN  = os.environ.get('CURSORI_ORACLE_DSN',
                                     os.environ.get('RIO_DASH_ORACLE_DSN',
                                                    'Srvoracle.groscidac.local:1521/GOLDPROD'))
CURSORI_ORACLE_USER = os.environ.get('CURSORI_ORACLE_USER', 'GOLDCEN')
CURSORI_ORACLE_PASS = os.environ.get('CURSORI_ORACLE_PASS',
                                     os.environ.get('RIO_DASH_ORACLE_PASS', ''))
# Fallback dev: se la password non è nell'ambiente, leggila da un file locale
# NON committato (C:\portale\django\.oracle_pass). Evita la fragilità del passaggio
# di variabili d'ambiente attraverso npm/PowerShell.
if not CURSORI_ORACLE_PASS:
    try:
        _pwfile = PROJECT_ROOT / '.oracle_pass'
        if _pwfile.exists():
            CURSORI_ORACLE_PASS = _pwfile.read_text(encoding='utf-8').strip()
    except Exception:
        pass

# =========================================================================
#  RIO FORNITORI (srviisnew) - trasferimento proposta a Gold via Python
#  Sostituisce trasffileriodash.exe. Le PASSWORD vanno messe in env
#  (RIO_DASH_SFTP_PASS, RIO_DASH_ORACLE_PASS); host/utenti hanno i default
#  storici dell'exe per comodita'.
# =========================================================================
RIO_DASH_SFTP_HOST   = os.environ.get('RIO_DASH_SFTP_HOST', '172.17.10.41')
RIO_DASH_SFTP_PORT   = int(os.environ.get('RIO_DASH_SFTP_PORT', '22'))
RIO_DASH_SFTP_USER   = os.environ.get('RIO_DASH_SFTP_USER', 'glpcenadm')
RIO_DASH_SFTP_PASS   = os.environ.get('RIO_DASH_SFTP_PASS', '')
RIO_DASH_SFTP_DEST   = os.environ.get('RIO_DASH_SFTP_DEST', '/gold/glp/central/gaia/RECEIVED/')
RIO_DASH_SSH_CMD     = os.environ.get('RIO_DASH_SSH_CMD', '/gold/glp/central/shell/./gc_xls_xlsord.sh')

RIO_DASH_ORACLE_DSN  = os.environ.get('RIO_DASH_ORACLE_DSN', 'Srvoracle.groscidac.local:1521/GOLDPROD')
RIO_DASH_ORACLE_USER = os.environ.get('RIO_DASH_ORACLE_USER', 'GOLDCEN')
RIO_DASH_ORACLE_PASS = os.environ.get('RIO_DASH_ORACLE_PASS', '')
RIO_DASH_ORACLE_PROC = os.environ.get('RIO_DASH_ORACLE_PROC', 'sil_rioDash')

# Formato CSV (deve combaciare con quello che si aspetta il loader Oracle / bcp)
RIO_DASH_CSV_SEP      = ';'
RIO_DASH_CSV_NEWLINE  = '\r\n'
RIO_DASH_CSV_ENCODING = 'utf-8'

# DRY RUN: se attivo la SP gira e il CSV viene generato/salvato su disco, ma
# NON si fa SFTP/Oracle/SSH e NON si tocca lo stato in t_fileRiodash/t_exportfoRiodash.
# Default attivo (sicuro): per il trasferimento reale impostare RIO_DASH_DRY_RUN=0 in env.
RIO_DASH_DRY_RUN = os.environ.get('RIO_DASH_DRY_RUN', '1').strip().lower() not in ('0', 'false', 'no')
# Cartella dove salvare il CSV in dry-run (default: logs del progetto)
RIO_DASH_DRY_RUN_DIR = os.environ.get('RIO_DASH_DRY_RUN_DIR', str(PROJECT_ROOT / 'logs'))

DATABASE_ROUTERS = [
    'project_core.routers.GoldReportRouter',
    'project_core.routers.CursoriRouter',
    'project_core.routers.CategoryRouter',
    'project_core.routers.ImportelabRouter',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'modules.portal.context_processors.portal_menu',
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATICFILES_DIRS = [PROJECT_ROOT / 'static']
X_FRAME_OPTIONS = 'SAMEORIGIN'
ELAB_SOURCE_DIR = r"C:\importelab\ordini"

ADMINS = [
    ('Tecnico', 'tecnico@groscidac.it'),
]
EMAIL_HOST = 'Srvmail.groscidac.local'
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'Portale Groscidac <noreply@groscidac.it>'
SERVER_EMAIL = 'noreply@groscidac.it'
#print(f"--- [DEBUG] FINE ESECUZIONE BASE.PY. ROOT_URLCONF è definito? {'ROOT_URLCONF' in locals()} ---")