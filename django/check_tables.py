import django, os, sys
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'project_core.settings.prod'
os.environ['DJANGO_ENV'] = 'prod'
django.setup()
from django.db import connections
with connections['default'].cursor() as cur:
    cur.execute(
        "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'piano_promo_promosessioneriga' "
        "ORDER BY ORDINAL_POSITION"
    )
    for row in cur.fetchall():
        print(row)
