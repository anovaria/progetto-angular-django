# project_core/settings/prod.py)

from .base import *
import os

ENV = os.environ.get("DJANGO_ENV", "prod").lower()

print(f"--- Caricamento impostazioni per ambiente: {ENV} ---")

# -------------------------------------------------------------------------
# LOGICA CONDIZIONALE PER PROD vs. TEST
# -------------------------------------------------------------------------

if ENV == 'test':
    DEBUG = False
    ADMINS = []  # disabilita email di errore in test
    ALLOWED_HOSTS = [
        'portale-test.groscidac.local',
        '127.0.0.1',
        'localhost',
    ]

    CSRF_TRUSTED_ORIGINS = [
        'https://portale-test.groscidac.local',
        'http://portale-test.groscidac.local',
    ]

    # Django puro: IIS fa da reverse proxy HTTPS→HTTP locale
    # Necessario per redirect corretti e request.is_secure()
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    LOGIN_URL = '/portal/login/'

    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': 'DjangoIntranet-test',
            'USER': os.environ.get('DB_DEFAULT_USER'),
            'PASSWORD': os.environ.get('DB_DEFAULT_PASSWORD'),
            'HOST': os.environ.get('DB_DEFAULT_HOST', '172.17.10.52'),
            'OPTIONS': {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
            },
        },
        'goldreport': {
            'ENGINE': 'mssql',
            'NAME': 'Db_GoldReport',
            'USER': os.environ.get('DB_GOLD_USER'),
            'PASSWORD': os.environ.get('DB_GOLD_PASSWORD'),
            'HOST': os.environ.get('DB_GOLD_HOST', '172.17.10.52'),
            'OPTIONS': {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
            },
        },
        'category': {
            'ENGINE': 'mssql',
            'NAME': os.environ.get('DB_CATEGORY_NAME', 'Db_Category'),
            'USER': os.environ.get('DB_GOLD_USER'),
            'PASSWORD': os.environ.get('DB_GOLD_PASSWORD'),
            'HOST': os.environ.get('DB_GOLD_HOST', '172.17.10.52'),
            'OPTIONS': {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
            },
        },
    }

elif ENV == 'prod':
    DEBUG = False

    ALLOWED_HOSTS = [
        'portale.groscidac.local',
        '127.0.0.1',
        'localhost',
    ]

    CORS_ALLOWED_ORIGINS = [
        "https://portale.groscidac.local",
    ]

    CSRF_TRUSTED_ORIGINS = [
        'https://portale.groscidac.local',
        'http://portale.groscidac.local',
    ]

    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    LOGIN_URL = '/'

    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': os.environ.get('DB_DEFAULT_NAME', 'DjangoIntranet'),
            'USER': os.environ.get('DB_DEFAULT_USER'),
            'PASSWORD': os.environ.get('DB_DEFAULT_PASSWORD'),
            'HOST': os.environ.get('DB_DEFAULT_HOST', '172.17.10.52'),
            'OPTIONS': {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
            },
        },
        'goldreport': {
            'ENGINE': 'mssql',
            'NAME': 'Db_GoldReport',
            'USER': os.environ.get('DB_GOLD_USER'),
            'PASSWORD': os.environ.get('DB_GOLD_PASSWORD'),
            'HOST': os.environ.get('DB_GOLD_HOST', '172.17.10.52'),
            'OPTIONS': {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
            },
        },
        'category': {
            'ENGINE': 'mssql',
            'NAME': os.environ.get('DB_CATEGORY_NAME', 'Db_Category'),
            'USER': os.environ.get('DB_GOLD_USER'),
            'PASSWORD': os.environ.get('DB_GOLD_PASSWORD'),
            'HOST': os.environ.get('DB_GOLD_HOST', '172.17.10.52'),
            'OPTIONS': {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
            },
        },
    }

# Comune a entrambi gli ambienti
LOGGING['handlers']['file']['filename'] = str(PROJECT_ROOT / 'logs' / 'django_prod.log')
FORCE_SCRIPT_NAME = None
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
PORTAL_ENVIRONMENT = ENV  # 'prod' o 'test' in base a DJANGO_ENV
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': f'C:/portale/django/cache_{ENV}',
    }
}