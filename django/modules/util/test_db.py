from django.db import connections

def test_goldreport_connection():
    with connections['goldreport'].cursor() as cursor:
        cursor.execute("SELECT TOP 5 * FROM ViniVda")  # sostituisci con una tabella reale
        rows = cursor.fetchall()
    return rows
