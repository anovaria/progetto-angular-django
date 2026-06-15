import os
from pathlib import Path
import sys
import waitress

# 1. PERCORSO DEL PROGETTO (C:\inetpub\PortaleIntranet\django)
PROJECT_ROOT = Path(__file__).resolve().parent

# ====================================================================
# AGGIUNTA FORZATA DEL PERCORSO CRITICO
# ====================================================================
# Aggiunge la radice del progetto al percorso di ricerca di Python. 
# Questo garantisce che Python trovi la cartella 'project_core'.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT)) 
# ====================================================================

# 2. DEFINISCE L'AMBIENTE
DJANGO_ENV = os.environ.get("DJANGO_ENV", "prod").lower()

# 3. Imposta il modulo settings (si basa su NSSM/os.environ)
# Deve essere impostato PRIMA di get_wsgi_application().
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_core.settings.prod")

# (La logica .env rimane qui)
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / f".env.{DJANGO_ENV}"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# 4. Carica l'applicazione WSGI
# Questa riga innesca il caricamento effettivo del modulo settings
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


if __name__ == "__main__":
    host = os.environ.get("DJANGO_HOST", "127.0.0.1")
    port = int(os.environ.get("DJANGO_PORT", 8000))
    threads = int(os.environ.get("DJANGO_THREADS", 4))

    print("="*50)
    print(f"Django Server ({DJANGO_ENV})")
    print(f"Listening on: http://{host}:{port}")
    print("="*50)

    waitress.serve(application, host=host, port=port, threads=threads, channel_timeout=120)