import os
import sys
from pathlib import Path

# 1. Configura i percorsi (Simula run_server.py)
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(f"Percorso Python aggiunto: {PROJECT_ROOT}")

# 2. Imposta le Variabili d'Ambiente CRITICHE (Simula NSSM)
# Modifica questi valori se necessario per il test
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_core.settings.prod")
os.environ.setdefault("DJANGO_SECRET_KEY", "chiave-di-test-per-debug-123")
os.environ.setdefault("DJANGO_ENV", "prod")

print(f"Usando settings: {os.environ['DJANGO_SETTINGS_MODULE']}")

# 3. Prova a caricare le impostazioni
try:
    from django.conf import settings
    print("--- Tentativo di accesso a ROOT_URLCONF ---")
    print(f"ROOT_URLCONF è: {settings.ROOT_URLCONF}")
    print("SUCCESS: Le impostazioni sono state caricate correttamente!")
except Exception as e:
    print("\n" + "="*50)
    print("ERRORE DURANTE IL CARICAMENTO DELLE IMPOSTAZIONI")
    print("="*50)
    print(f"Tipo Errore: {type(e).__name__}")
    print(f"Messaggio: {e}")
    import traceback
    traceback.print_exc()