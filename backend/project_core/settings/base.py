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
    'modules.plu',
    'modules.importelab',
    'modules.pallet_promoter',
    'modules.alloca_hostess',
    'modules.merchandiser',
    'modules.welfare',
    'modules.asso_articoli',
    'modules.scaricopromo',
    'modules.active_users',
]

# Middleware (Nessun cambiamento)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', # Spostato in cima per sicurezza (base.py)
    'django.contrib.sessions.middleware.SessionMiddleware',
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
    'root': {'handlers': ['file', 'console'], 'level': 'DEBUG'},
}

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.environ.get('DB_DEFAULT_NAME', 'DjangoIntranet'),
        'USER': os.environ.get('DB_DEFAULT_USER', 'dev_django_user'),
        'PASSWORD': os.environ.get('DB_DEFAULT_PASSWORD', 'dev_password_only'),
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
        'PASSWORD': os.environ.get('DB_GOLD_PASSWORD', 'dev_password_only'),
        'HOST': os.environ.get('DB_GOLD_HOST', 'localhost\\SQLEXPRESS'),
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'importelab' / 'db.sqlite3',
    },
}
DATABASE_ROUTERS = [
    'project_core.routers.GoldReportRouter',
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
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# In produzione usa SAMEORIGIN (Angular e Django stesso dominio via IIS)
X_FRAME_OPTIONS = 'SAMEORIGIN'
ELAB_SOURCE_DIR = r"C:\\Paolo"
#print(f"--- [DEBUG] FINE ESECUZIONE BASE.PY. ROOT_URLCONF è definito? {'ROOT_URLCONF' in locals()} ---")