# check_labels.py
import os
import django

# Imposta la variabile ambiente corretta
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_core.settings.prod')

django.setup()

from django.apps import apps

labels = {}
for app_config in apps.get_app_configs():
    label = app_config.label
    if label in labels:
        print(f"⚠️  DUPLICATO: {label} -> {app_config.name} e {labels[label]}")
    else:
        labels[label] = app_config.name
        print(f"{label} -> {app_config.name}")

print("\n✅ Verifica completata")
