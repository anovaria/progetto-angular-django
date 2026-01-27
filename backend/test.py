import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_core.settings.dev')
django.setup()

from modules.plu.views import execute_plu_query

results = execute_plu_query()
for r in results[:5]:
    ean = r.get('ean')
    ean_fmt = r.get('ean_formatted')
    print(f"EAN raw: [{ean}] len={len(str(ean or ''))}")
    print(f"EAN fmt: [{ean_fmt}] len={len(str(ean_fmt or ''))}")
    print("---")