import django, os, sys
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'project_core.settings.prod'
os.environ['DJANGO_ENV'] = 'test'
django.setup()

from django.db import connections

COD_ART = '882437'

sql = """
    SELECT
        [Cod. Piano Gold]      AS cod_piano_gold,
        [Cod.Art.]             AS cod_art,
        [Ordine in Corso]      AS ordine_in_corso,
        [Data di Consegna]     AS data_consegna,
        [Prezzo Promo]         AS prezzo_promo
    FROM r_pianopromofuturo
    WHERE [Cod.Art.] = %s
    ORDER BY [Cod. Piano Gold]
"""

with connections['goldreport'].cursor() as cur:
    cur.execute(sql, [COD_ART])
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]

print(f"Righe trovate per cod_art '{COD_ART}': {len(rows)}")
for r in rows:
    val = r.get('ordine_in_corso')
    print(f"  piano={r['cod_piano_gold']!r}  ordine_in_corso={val!r}  type={type(val).__name__}")
