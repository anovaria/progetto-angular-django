import django
import os
import sys

sys.path.insert(0, r'C:\portale\django')

ambiente = input("Ambiente (dev/test/prod): ").strip().lower()

if ambiente == 'dev':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'project_core.settings.dev'
elif ambiente == 'test':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'project_core.settings.prod'
    os.environ['DJANGO_ENV'] = 'test'
elif ambiente == 'prod':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'project_core.settings.prod'
    os.environ['DJANGO_ENV'] = 'prod'
else:
    print("Ambiente non valido.")
    sys.exit(1)

django.setup()

from django.core.cache import cache

titolo = input("Titolo: ")
testo = input("Testo: ")
destinatari_input = input("Destinatari (username separati da virgola, invio per tutti): ").strip()

if destinatari_input:
    destinatari = [d.strip() for d in destinatari_input.split(',')]
else:
    destinatari = []

durata = input("Durata in minuti (invio per 60): ").strip()
durata_secondi = int(durata) * 60 if durata else 3600

cache.set('sitemsg_urgente', {
    'titolo': titolo,
    'testo': testo,
    'destinatari': destinatari
}, timeout=durata_secondi)

print(f"Messaggio inviato in {ambiente} per {durata_secondi // 60} minuti!")