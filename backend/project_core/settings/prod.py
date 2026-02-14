# project_core/settings/prod.py)

from .base import *
import os

# ... (Tutta la logica e le definizioni iniziali di base.py) ...

# 2. DEFINIZIONE DELL'AMBIENTE E CONFIGURAZIONI CHIAVE
# Legge la variabile di contesto (prod o test)
ENV = os.environ.get("DJANGO_ENV", "prod").lower()

print(f"--- Caricamento impostazioni per ambiente: {ENV} ---")

# -------------------------------------------------------------------------
# LOGICA CONDIZIONALE PER PROD vs. TEST
# -------------------------------------------------------------------------

if ENV == 'test':
    
    # 1. DEBUG: Tipicamente True in test, False per performance
    DEBUG = False
    
    # 2. HOSTS consentiti per Staging (URL del sito di test)
    # >>> AGGIUNTA DELL'URL SPECIFICO DI STAGING <<<
    ALLOWED_HOSTS = [
        'portale-test.groscidac.local',
        '127.0.0.1',
        'localhost',        
    ]
    
    # 3. CORS: Solo l'origine del frontend di Staging (per le richieste AJAX)
    # >>> AGGIUNTA DELL'ORIGINE SPECIFICA DI STAGING (senza / finale) <<<
    CORS_ALLOWED_ORIGINS = [
        "https://portale-test.groscidac.local",
    ]
    CSRF_TRUSTED_ORIGINS = [
        'https://portale-test.groscidac.local',
    ]
    
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
    ]
    
    # Sicurezza SSL/Proxy
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
# Log file per produzione
LOGGING['handlers']['file']['filename'] = str(PROJECT_ROOT / 'logs' / 'django_prod.log')
# URL settings
FORCE_SCRIPT_NAME = None
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
LOGIN_URL = '/'

# 4. SICUREZZA SSL/PROXY (CRUCIALE)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
PORTAL_ENVIRONMENT = ENV  # 'prod' o 'test' in base a DJANGO_ENV