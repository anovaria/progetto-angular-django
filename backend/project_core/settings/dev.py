from .base import *

DEBUG = True
DJANGO_ENV = 'dev'

# Hosts consentiti per sviluppo locale
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# CSRF per Angular dev server
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:4200',
    'http://127.0.0.1:4200',
]

# CORS per Angular dev server
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]
CORS_ALLOW_CREDENTIALS = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# URL settings
FORCE_SCRIPT_NAME = None
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
LOGIN_URL = '/'

# =========================================================================
# DATABASE PER SVILUPPO - Usa credenziali corrette
# =========================================================================

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'DjangoIntranet',
        'USER': 'django_user',
        'PASSWORD': 'Sangiovese.2025@@',  # ← Metti la password corretta qui
        'HOST': '172.17.10.52',
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
    'goldreport': {
        'ENGINE': 'mssql',
        'NAME': 'Db_GoldReport',
        'USER': 'django_user',
        'PASSWORD': 'Sangiovese.2025@@',  # ← Metti la password corretta qui
        'HOST': '172.17.10.52',
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no;TrustServerCertificate=yes',
        },
    },
}

DATABASE_ROUTERS = ['project_core.routers.GoldReportRouter']

# Logging solo su console per sviluppo
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
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
# ========================================
# LOGGING CONFIGURATION
# ========================================

import os

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    
    'loggers': {
        # Root logger
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # SSO Middleware (molto verboso)
        'modules.auth.middleware.sso_middleware': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        
        # Auth module
        'modules.auth': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    
    # Root logger default
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
# ========================================
# COOKIE SETTINGS FOR DEV
# ========================================

# Session settings - DEV
SESSION_COOKIE_SAMESITE = 'Lax'  # ← Cambia da None (in base.py)
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = '/'

# CSRF settings - DEV
CSRF_COOKIE_SAMESITE = 'Lax'  # ← Cambia da None (in base.py)
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
# =========================================================================
# IFRAME - Permetti embedding in Angular (porte diverse in dev)
# =========================================================================
MIDDLEWARE = [m for m in MIDDLEWARE if m != 'django.middleware.clickjacking.XFrameOptionsMiddleware']
PORTAL_ENVIRONMENT = 'dev'