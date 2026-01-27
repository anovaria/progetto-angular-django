# test_plu_connection.py - VERSIONE CORRETTA
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_core.settings.dev')
django.setup()

from django.db import connections
from modules.plu.models import RepartoPlu

def test_database_connection():
    print("=" * 70)
    print("TEST 1: Connessione Database")
    print("=" * 70)
    try:
        with connections['goldreport'].cursor() as cursor:
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()
            print("✅ Connessione al database GOLDREPORT riuscita!")
            print(f"   SQL Server Version: {version[0][:50]}...")
            return True
    except Exception as e:
        print(f"❌ Errore connessione database: {e}")
        return False

def test_view_exists():
    print("\n" + "=" * 70)
    print("TEST 2: Esistenza View V_RepartoPlu")
    print("=" * 70)
    try:
        with connections['goldreport'].cursor() as cursor:
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_TYPE 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'V_RepartoPlu'
            """)
            result = cursor.fetchone()
            if result:
                print(f"✅ View trovata: {result[0]} ({result[1]})")
                return True
            else:
                print("❌ View V_RepartoPlu non trovata!")
                return False
    except Exception as e:
        print(f"❌ Errore verifica view: {e}")
        return False

def test_view_structure():
    print("\n" + "=" * 70)
    print("TEST 3: Struttura View")
    print("=" * 70)
    try:
        with connections['goldreport'].cursor() as cursor:
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'V_RepartoPlu'
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()
            print(f"✅ View ha {len(columns)} colonne:\n")
            for col in columns:
                col_name, data_type, max_len, nullable = col
                length = f"({max_len})" if max_len else ""
                null_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"   - {col_name:20s} {data_type}{length:10s} {null_str}")
            return True
    except Exception as e:
        print(f"❌ Errore verifica struttura: {e}")
        return False

def test_data_count():
    print("\n" + "=" * 70)
    print("TEST 4: Conteggio Dati")
    print("=" * 70)
    try:
        count = RepartoPlu.objects.using('goldreport').count()
        print(f"✅ Trovati {count:,} articoli nella view")
        if count == 0:
            print("⚠️  Warning: Nessun dato trovato nella view!")
        return True
    except Exception as e:
        print(f"❌ Errore conteggio dati: {e}")
        return False

def test_sample_data():
    print("\n" + "=" * 70)
    print("TEST 5: Lettura Dati di Esempio")
    print("=" * 70)
    try:
        articoli = RepartoPlu.objects.using('goldreport').all()[:5]
        if not articoli:
            print("⚠️  Nessun dato disponibile per il test")
            return False
        
        print(f"✅ Letti {len(articoli)} articoli di esempio:\n")
        for art in articoli:
            # Usa :s per stringhe invece di :d per decimali
            plu_str = art.plu or 'N/A'
            desc_str = (art.descrizione or 'N/A')[:40]
            rep_str = art.rep or 'N/A'
            banco_str = art.bancobilancia or 'N/A'
            print(f"   PLU {plu_str:>7s} | {desc_str:40s} | Rep: {rep_str:>3s} | Banco: {banco_str:>2s}")
        return True
    except Exception as e:
        print(f"❌ Errore lettura dati: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_reparti_breakdown():
    print("\n" + "=" * 70)
    print("TEST 6: Breakdown per Reparto")
    print("=" * 70)
    try:
        from django.db.models import Count
        reparti = RepartoPlu.objects.using('goldreport').values('rep').annotate(
            totale=Count('codArticolo')
        ).order_by('rep')
        
        print(f"✅ Trovati {len(reparti)} reparti:\n")
        for rep_data in reparti:
            rep_obj = RepartoPlu(rep=rep_data['rep'])
            rep_str = rep_data['rep'] or 'N/A'
            print(f"   Rep {rep_str:>3s} - {rep_obj.reparto_nome:25s}: {rep_data['totale']:4d} articoli")
        return True
    except Exception as e:
        print(f"❌ Errore breakdown reparti: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_duplicati_plu():
    print("\n" + "=" * 70)
    print("TEST 7: Check PLU Duplicati")
    print("=" * 70)
    try:
        from django.db.models import Count
        duplicati = RepartoPlu.objects.using('goldreport').values(
            'bancobilancia', 'plu'
        ).annotate(
            count=Count('codArticolo')
        ).filter(count__gt=1).order_by('-count')[:10]
        
        if duplicati:
            print(f"⚠️  Trovati {len(duplicati)} gruppi di PLU duplicati:\n")
            for dup in duplicati:
                banco = dup['bancobilancia'] or 'N/A'
                plu = dup['plu'] or 'N/A'
                print(f"   Banco {banco:>2s} | PLU {plu:>7s} | {dup['count']} articoli")
        else:
            print("✅ Nessun PLU duplicato trovato!")
        return True
    except Exception as e:
        print(f"❌ Errore check duplicati: {e}")
        return False

def main():
    print("\n" + "=" * 70)
    print("TEST MODULO PLU - Verifica Installazione")
    print("=" * 70 + "\n")
    
    tests = [
        test_database_connection,
        test_view_exists,
        test_view_structure,
        test_data_count,
        test_sample_data,
        test_reparti_breakdown,
        test_duplicati_plu,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Errore inaspettato nel test {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("RIEPILOGO TEST")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"\nTest passati: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 TUTTI I TEST PASSATI! Il modulo PLU è pronto per l'uso.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test falliti. Verifica la configurazione.")
        return 1

if __name__ == '__main__':
    sys.exit(main())