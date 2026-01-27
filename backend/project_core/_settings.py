from datetime import timedelta
import os
from pathlib import Path
import sys, socket

print("DJANGO_ENV:", os.environ.get("DJANGO_ENV"), file=sys.stderr)

BASE_DIR = Path(__file__).resolve().parent.parent
DJANGO_ENV = os.environ.get("DJANGO_ENV", "development").lower()
DEBUG = DJANGO_ENV != "production"
ROOT_URLCONF = "project_core.urls"

# ----------------------
# STATIC
# ----------------------
if DJANGO_ENV == "production":
    FORCE_SCRIPT_NAME = "/django"
    STATIC_URL = "/django/static/"
    LOGIN_URL = '/django/admin/login/'
else:
    FORCE_SCRIPT_NAME = None
    STATIC_URL = "/static/"
    LOGIN_URL = '/'

STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ----------------------
# APPS
# ----------------------
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
]
INSTALLED_APPS += [
    'modules.auth',
    'modules.util',
]

# ----------------------
# MIDDLEWARE
# ----------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ----------------------
# AUTH
# ----------------------
AUTHENTICATION_BACKENDS = [
    'modules.auth.backends.LDAPBackend',         # <---- AGGIUNGI QUI
    'django.contrib.auth.backends.RemoteUserBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ----------------------
# REST FRAMEWORK
# ----------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# ----------------------
# DATABASES
# ----------------------
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.getenv('DB_NAME'),           # Legge "intranet_db" dal .env
        'USER': os.getenv('DB_USER'),           # Legge "django_user" dal .env
        'PASSWORD': os.getenv('DB_PASSWORD'),   # Legge la password dal .env
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '1433'),
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
    'goldreport': {
        'ENGINE': 'mssql',
        'NAME': 'Db_GoldReport',
        'USER': 'django_user',
        'PASSWORD': 'Sangiovese.2025@@',
        'HOST': '172.17.10.52',
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
}


DATABASE_ROUTERS = ['project_core.routers.GoldReportRouter']

# ----------------------
# SECURITY
# ----------------------
SECRET_KEY = 'django-insecure-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', socket.gethostname()]
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = []

# ----------------------
# TEMPLATES
# ----------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ROOT_URLCONF = 'project_core.urls'
WSGI_APPLICATION = 'project_core.wsgi.application'

# ----------------------
# LOGGING
# -------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django_auth_ldap': {
            'handlers': ['console'],
            'level': 'DEBUG', # Molto importante: livello DEBUG
            'propagate': True,
        },
    },
}


"""
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'DEBUG',
    },
}
"""