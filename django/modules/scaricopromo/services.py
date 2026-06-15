"""
Scarico Promo - Business Logic (services.py)
Replica la logica VBA di M_esporta e delle query Access.
"""
import csv
import io
import os
from datetime import datetime, timedelta
from django.db import connection, connections
from django.conf import settings

from .models import (
    MettereInA, MettereInE, MettereInF, MettereInI, MettereInK, MettereInS,
    NonPossoMettereInA, ChiudiAttri, ApriAttri, AggiornaAttri,
    PerExport, PerExportStorico,
)


# ============================================================
# PATH EXPORT (replica \\srvnas\...\OfferteFreschi\exp\)
# ============================================================

EXPORT_PATH = getattr(
    settings,
    'SCARICOPROMO_EXPORT_PATH',
    r'\\srvnas\Groscidac\Programmi Aziendali\OfferteFreschi\exp'
)


def get_timestamp():
    """Formato timestamp come in VBA: ddmmyy_hhmmss"""
    return datetime.now().strftime('%d%m%y_%H%M%S')

def format_date_ddmmyyyy(val):
    """Converte qualsiasi formato data in dd/mm/yyyy."""
    if not val:
        return ''
    val = str(val).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(val, fmt).strftime('%d/%m/%Y')
        except ValueError:
            continue
    return val
# ============================================================
# LETTURA DA GOLD (read-only, via goldreport DB)
# ============================================================

def get_gold_cursor():
    """Restituisce un cursore al database Gold (read-only)."""
    return connections['goldreport'].cursor()


def verifica_ccom(ccom):
    """Verifica che il CCOM esista in t_artfrepromo."""
    ccom = ccom.strip()
    with get_gold_cursor() as cursor:
        cursor.execute(
            "SELECT TOP 1 CCOM, RAGIONESOCIALE FROM t_artfrepromo WHERE CCOM = %s",
            [ccom]
        )
        row = cursor.fetchone()
    if not row:
        return {'found': False, 'message': f'CCOM non trovato: {ccom}'}
    return {
        'found': True,
        'ccom': str(row[0] or '').strip(),
        'descrizione': str(row[1] or '').strip(),
    }


def carica_articoli_da_ccom(ccom, model):
    """
    Carica tutti gli articoli di un CCOM da t_artfrepromo in una tabella MettereInX.
    Evita duplicati (non reinserisce codart già presenti).
    Restituisce il numero di articoli aggiunti.
    """
    ccom = ccom.strip()
    with get_gold_cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT CEXR FROM t_artfrepromo WHERE CCOM = %s AND CEXR IS NOT NULL AND CEXR <> ''",
            [ccom]
        )
        rows = cursor.fetchall()

    if not rows:
        return 0

    esistenti = set(model.objects.values_list('codart', flat=True))
    nuovi = [
        model(codart=str(r[0]).strip(), ccom=ccom)
        for r in rows
        if str(r[0]).strip() not in esistenti
    ]
    if nuovi:
        model.objects.bulk_create(nuovi)
    return len(nuovi)


def verifica_codart(codart):
    """
    Verifica che il codice articolo esista in GoldReport.
    Accetta sia CODART che EAN (converte EAN -> CODART).
    Strategia a cascata:
      1. v_AllArticolo per CODART esatto (senza filtro EANPRINC)
      2. v_AllArticolo per EAN con EANPRINC=1 (evita duplicati)
      3. t_ArticoliGiacTutti come ultimo fallback
    """
    codart = codart.strip().upper()

    def _row_to_result(row):
        return {
            'found': True,
            'codart': str(row[0] or '').strip(),
            'descrizione': str(row[1] or '').strip() if len(row) > 1 and row[1] else '',
        }

    with get_gold_cursor() as cursor:

        # 1. Cerca per CODART esatto in v_AllArticolo (senza vincoli EANPRINC)
        try:
            cursor.execute(
                "SELECT TOP 1 CODART, DESCRIZIONE FROM v_AllArticolo WHERE CODART = %s",
                [codart]
            )
            row = cursor.fetchone()
            if row:
                return _row_to_result(row)
        except Exception:
            try:
                cursor.execute(
                    "SELECT TOP 1 CODART, NULL FROM v_AllArticolo WHERE CODART = %s",
                    [codart]
                )
                row = cursor.fetchone()
                if row:
                    return _row_to_result(row)
            except Exception:
                pass

        # 2. Cerca per EAN (EANPRINC=1 per tornare un solo CODART)
        try:
            cursor.execute(
                "SELECT TOP 1 CODART, DESCRIZIONE FROM v_AllArticolo WHERE EAN = %s AND EANPRINC = 1",
                [codart]
            )
            row = cursor.fetchone()
            if row:
                return _row_to_result(row)
        except Exception:
            try:
                cursor.execute(
                    "SELECT TOP 1 CODART, NULL FROM v_AllArticolo WHERE EAN = %s AND EANPRINC = 1",
                    [codart]
                )
                row = cursor.fetchone()
                if row:
                    return _row_to_result(row)
            except Exception:
                pass

        # 3. Fallback su t_ArticoliGiacTutti
        try:
            cursor.execute(
                "SELECT TOP 1 CODARTICOLO, NULL FROM t_ArticoliGiacTutti WHERE CODARTICOLO = %s",
                [codart]
            )
            row = cursor.fetchone()
            if row:
                return _row_to_result(row)
        except Exception:
            pass

    return {'found': False, 'message': f'Articolo non trovato: {codart}'}


def get_descrizioni_bulk(codarts):
    """
    Restituisce un dict {codart: descrizione} per una lista di codici articolo.
    Interroga v_AllArticolo (goldreport).
    """
    if not codarts:
        return {}
    placeholders = ','.join(['%s'] * len(codarts))
    result = {}
    with get_gold_cursor() as cursor:
        try:
            cursor.execute(
                f"SELECT CODART, DESCRART FROM v_AllArticolo WHERE CODART IN ({placeholders})",
                list(codarts)
            )
            for row in cursor.fetchall():
                result[str(row[0] or '').strip()] = str(row[1] or '').strip()
        except Exception:
            pass
    return result


def query_sargc_for_metterein(table_name, codart_field='codart', extra_where=''):
    """
    Replica le query ChiudiAttri-X.
    LEFT JOIN 'Mettere in X' con dbo_t_SARGC, restituisce attributi.
    
    Dato che le tabelle 'Mettere in X' sono su DjangoIntranet e SARGC su Gold,
    facciamo prima la lettura dei codart e poi query su Gold.
    """
    # 1. Leggi i codici articolo dalla tabella locale
    model_map = {
        'A': MettereInA, 'E': MettereInE, 'F': MettereInF,
        'I': MettereInI, 'K': MettereInK, 'S': MettereInS,
    }
    model = model_map.get(table_name)
    if not model:
        return []

    codici = list(model.objects.values_list(codart_field, flat=True))
    if not codici:
        return []

    # 2. Query su Gold per ottenere attributi SARGC
    placeholders = ','.join(['%s'] * len(codici))
    
    sql = f"""
        SELECT CODART, COD, ST, ALPHA, DTAINI, DTACH
        FROM t_SARGC
        WHERE CODART IN ({placeholders})
          AND CODART IS NOT NULL
          AND CODART <> ''
    """
    
    if extra_where:
        sql += f" AND {extra_where}"
    
    sql += " ORDER BY CODART"

    with get_gold_cursor() as cursor:
        cursor.execute(sql, codici)
        rows = cursor.fetchall()

    return rows


# ============================================================
# FLUSSO CHIUDI/APRI ATTRIBUTI
# (replica Comando15_Click di M_esporta)
# ============================================================

def svuota_tabelle_lavoro():
    """Replica q_SvuotaAttri: svuota ChiudiAttri, ApriAttri, AggiornaAttri."""
    ChiudiAttri.objects.all().delete()
    ApriAttri.objects.all().delete()
    AggiornaAttri.objects.all().delete()


def chiudi_attri(stato, extra_where=''):
    """
    Replica ChiudiAttri-X.
    Legge da 'Mettere in X' + SARGC e popola ChiudiAttri.
    """
    rows = query_sargc_for_metterein(stato, extra_where=extra_where)
    
    objs = []
    for row in rows:
        codart, cod, st, alpha, dtaini, dtach = row
        objs.append(ChiudiAttri(
            CodArticolo=codart or '',
            ClasseAttri=cod or '',
            CodAttri=st or '',
            ValoreNum='',
            ValoreAlpha=alpha or '',
            ValoreData='',
            DtaIniz=dtaini or '',
            DTACH=dtach or '',
        ))
    
    if objs:
        ChiudiAttri.objects.bulk_create(objs)
    
    return len(objs)


def chiudi_attri_n():
    """
    Replica ChiudiAttri-N (caso speciale: no tabella 'Mettere in',
    legge direttamente da SARGC con filtri ST='N', GIACPDV<>0, S in (1,2,4)).
    """
    sql = """
        SELECT CODART, COD, ST, ALPHA, DTAINI, DTACH
        FROM t_SARGC
        WHERE CODART <> ''
          AND ST = 'N'
          AND GIACPDV <> 0
          AND S IN ('1', '2', '4')
        ORDER BY CODART
    """
    with get_gold_cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    objs = []
    for row in rows:
        codart, cod, st, alpha, dtaini, dtach = row
        objs.append(ChiudiAttri(
            CodArticolo=codart or '',
            ClasseAttri=cod or '',
            CodAttri=st or '',
            ValoreNum='',
            ValoreAlpha=alpha or '',
            ValoreData='',
            DtaIniz=dtaini or '',
            DTACH=dtach or '',
        ))

    if objs:
        ChiudiAttri.objects.bulk_create(objs)

    return len(objs)


def apri_attri(nuovo_stato):
    """
    Replica q_ApriAttri-X.
    Da ChiudiAttri crea record in ApriAttri con nuovo stato,
    data inizio = DTACH + 1 giorno, fine = 31/12/2049.
    """
    chiusi = ChiudiAttri.objects.all()
    objs = []
    
    for c in chiusi:
        # Calcola data inizio = DTACH + 1 giorno
        dtaini = None
        try:
            if c.DTACH:
                # Prova vari formati data
                for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
                    try:
                        dt = datetime.strptime(c.DTACH.strip(), fmt)
                        dtaini = dt + timedelta(days=1)
                        break
                    except ValueError:
                        continue
        except Exception:
            pass

        objs.append(ApriAttri(
            CodArticolo=c.CodArticolo,
            ClasseAttri=c.ClasseAttri,
            CodAttri=nuovo_stato,
            ValoreNum='',
            ValoreAlpha='',
            ValoreData='',
            dtaini=dtaini,
            dtaFine='31/12/2049',
        ))

    if objs:
        ApriAttri.objects.bulk_create(objs)

    return len(objs)


def accoda_a_aggiorna():
    """
    Replica q_accodaChiudiAttri + q_accodaApriAttri.
    Copia da ChiudiAttri e ApriAttri verso AggiornaAttri.
    """
    count = 0

    # Accoda chiusure
    for c in ChiudiAttri.objects.all():
        dtaini = None
        try:
            if c.DtaIniz:
                for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
                    try:
                        dtaini = datetime.strptime(c.DtaIniz.strip(), fmt)
                        break
                    except ValueError:
                        continue
        except Exception:
            pass

        AggiornaAttri.objects.create(
            CodArticolo=c.CodArticolo,
            ClasseAttri=c.ClasseAttri,
            CodAttri=c.CodAttri,
            ValoreNum=c.ValoreNum,
            ValoreAlpha=c.ValoreAlpha,
            ValoreData=c.ValoreData,
            dtaini=dtaini,
            dtaFine=c.DTACH,
        )
        count += 1

    # Accoda aperture
    for a in ApriAttri.objects.all():
        AggiornaAttri.objects.create(
            CodArticolo=a.CodArticolo,
            ClasseAttri=a.ClasseAttri,
            CodAttri=a.CodAttri,
            ValoreNum=a.ValoreNum,
            ValoreAlpha=a.ValoreAlpha,
            ValoreData=a.ValoreData,
            dtaini=a.dtaini,
            dtaFine=a.dtaFine,
        )
        count += 1

    return count


def svuota_chiudi_apri():
    """Replica q_CancChiudiAttri + q_CancApriAttri."""
    ChiudiAttri.objects.all().delete()
    ApriAttri.objects.all().delete()


def elabora_attributi():
    """
    Replica l'intero flusso di Comando15_Click.
    Restituisce il path del CSV generato e il conteggio record.
    """
    # 1. Svuota tabelle di lavoro
    svuota_tabelle_lavoro()

    # 2. Ciclo per ogni tipo di stato
    # N -> I (chiudi N, apri I)
    chiudi_attri_n()
    apri_attri('I')
    accoda_a_aggiorna()
    svuota_chiudi_apri()

    # A (chiudi attributi da Mettere in A, apri A)
    chiudi_attri('A')
    apri_attri('A')
    accoda_a_aggiorna()
    svuota_chiudi_apri()

    # E
    chiudi_attri('E', extra_where="ST <> 'E'")
    apri_attri('E')
    accoda_a_aggiorna()
    svuota_chiudi_apri()

    # K
    chiudi_attri('K')
    apri_attri('K')
    accoda_a_aggiorna()
    svuota_chiudi_apri()

    # S
    chiudi_attri('S')
    apri_attri('S')
    accoda_a_aggiorna()
    svuota_chiudi_apri()

    # 3. Genera CSV in memoria
    csv_content, csv_filename = esporta_aggiorna_attributi_csv()

    # 4. Conta record generati
    tot = AggiornaAttri.objects.count()

    # 5. Svuota tabelle Mettere in X
    svuota_metterein()

    return csv_content, csv_filename, tot


# ============================================================
# VALIDAZIONE "METTERE IN A" (replica Comando3_Click di m_MettereA)
# ============================================================

def valida_mettere_in_a():
    """
    Replica il flusso di m_MettereA.Comando3_Click:
    1. Svuota NonPossoMettereInA
    2. Trova articoli con giacenza <> 0
    3. Accoda a dbo_t_chordine
    Restituisce lista articoli non processabili.
    """
    # Svuota
    NonPossoMettereInA.objects.all().delete()

    # Prendi codici da Mettere in A
    codici_a = list(MettereInA.objects.values_list('codart', 'ccom'))
    if not codici_a:
        return []

    codart_list = [c[0] for c in codici_a]
    codart_ccom_map = {c[0]: c[1] for c in codici_a}
    placeholders = ','.join(['%s'] * len(codart_list))

    # Query su Gold: articoli con giacenza
    sql = f"""
        SELECT DISTINCT CODARTICOLO, STATO, GIAC_PDV, GIAC_DEP
        FROM t_ArticoliGiacTutti
        WHERE CODARTICOLO IN ({placeholders})
          AND (GIAC_PDV <> 0 OR GIAC_DEP <> 0)
    """

    non_processabili = []
    with get_gold_cursor() as cursor:
        cursor.execute(sql, codart_list)
        rows = cursor.fetchall()

        for row in rows:
            codarticolo, stato, giac_pdv, giac_dep = row
            ccom = codart_ccom_map.get(codarticolo, '')
            NonPossoMettereInA.objects.create(codart=codarticolo, ccom=ccom)
            non_processabili.append({
                'codart': codarticolo,
                'ccom': ccom,
                'stato': stato,
                'giac_pdv': giac_pdv,
                'giac_dep': giac_dep,
            })

    # Accoda a T_chOrdine gli articoli senza giacenza
    accoda_chordine()

    return non_processabili


def accoda_chordine():
    """
    Replica q_accodaDaMettereASql.
    INSERT INTO T_chOrdine (Ccom, CodArticolo) da Mettere in A.
    Esclude articoli con giacenza (NonPossoMettereInA).
    Idempotente: elimina eventuali record NULL preesistenti prima di inserire.
    """
    records = list(MettereInA.objects.values_list('ccom', 'codart').distinct())
    if not records:
        return 0

    non_processabili = set(NonPossoMettereInA.objects.values_list('codart', flat=True))
    da_inserire = [(ccom, codart) for ccom, codart in records if codart not in non_processabili]

    if not da_inserire:
        return 0

    with connections['goldreport'].cursor() as cursor:
        for ccom, codart in da_inserire:
            ccom_val = ccom if ccom else None
            cursor.execute(
                "IF NOT EXISTS (SELECT 1 FROM T_chOrdine WHERE CodArticolo = %s AND flag IS NULL) "
                "INSERT INTO T_chOrdine (Ccom, CodArticolo) VALUES (%s, %s)",
                [codart, ccom_val, codart]
            )

    return len(da_inserire)


# ============================================================
# EXPORT CSV
# ============================================================

def esporta_aggiorna_attributi_csv():
    """
    Replica 'Esporta-AggiornaAttributi' salvato in Access.
    Genera CSV con i dati di AggiornaAttri. Restituisce (bytes, filename).
    """
    timestamp = get_timestamp()
    filename = f"{timestamp}_Attr.csv"

    records = AggiornaAttri.objects.all().values_list(
        'CodArticolo', 'ClasseAttri', 'CodAttri',
        'ValoreNum', 'ValoreAlpha', 'ValoreData',
        'dtaini', 'dtaFine'
    )

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=';')
    writer.writerow([
        'Codice articolo', 'Classe attributo', 'Codice attributo',
        'Valore numerico', 'Valore alfanumerico', 'Valore data',
        'Data inizio', 'Data fine'
    ])
    for r in records:
        row = list(r)
        row[6] = format_date_ddmmyyyy(row[6])  # Data inizio
        row[7] = format_date_ddmmyyyy(row[7])  # Data fine
        writer.writerow(row)

    return buf.getvalue().encode('utf-8-sig'), filename


def fmt_valore(val):
    """Converte valore numerico in formato italiano (virgola, senza zeri finali)."""
    if not val:
        return ''
    try:
        return f'{float(str(val).replace(",", ".")):.10g}'.replace('.', ',')
    except (ValueError, TypeError):
        return str(val)


def esporta_promo_csv():
    """
    Replica 'Esporta-Promo'.
    Genera CSV con tutti i dati promozione da t_perExport. Restituisce (bytes, filename).
    """
    timestamp = get_timestamp()
    filename = f"{timestamp}_Promo.csv"

    records = PerExport.objects.all().values_list(
        'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
        'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
        'SelezionePromozione', 'DataInizio', 'DataFine',
        'ScontoExtra', 'TipoSconto1', 'TipoSconto',
        'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
    )

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=';')
    writer.writerow([
        'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
        'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
        'SelezionePromozione', 'DataInizio', 'DataFine',
        'ScontoExtra', 'TipoSconto1', 'TipoSconto',
        'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
    ])
    for r in records:
        row = list(r)
        row[7] = format_date_ddmmyyyy(row[7])  # DataInizio
        row[8] = format_date_ddmmyyyy(row[8])  # DataFine
        try:
            s1 = float(str(row[9] or '').replace(',', '.').strip() or 0)
            s2 = float(str(row[10] or '').replace(',', '.').strip() or 0)
            s3 = float(str(row[15] or '').replace(',', '.').strip() or 0)
            if s1 > 0 and (s2 > 0 or s3 > 0):
                row[9] = fmt_valore(100 - (1 - s1 / 100) * (1 - s2 / 100) * (1 - s3 / 100) * 100)
                row[10] = ''                    # TipoSconto1 vuoto: cumulo già in ScontoExtra
                row[15] = ''                    # Valore1 vuoto: già incorporato nel cumulo
            else:
                row[9] = fmt_valore(row[9])
                row[15] = fmt_valore(row[15])
        except (ValueError, TypeError):
            row[9] = fmt_valore(row[9])
            row[15] = fmt_valore(row[15])
        row[14] = fmt_valore(row[14])           # Valore
        writer.writerow(row)

    return buf.getvalue().encode('utf-8-sig'), filename


def esporta_condacq_csv():
    """
    Replica 'Esporta-CondAcq'.
    Genera CSV solo per record con ScontoExtra > 0. Restituisce (bytes, filename).
    """
    timestamp = get_timestamp()
    filename = f"{timestamp}_CondAcq.csv"

    records = PerExport.objects.exclude(
        ScontoExtra=''
    ).exclude(
        ScontoExtra='0'
    ).values_list(
        'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
        'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
        'SelezionePromozione', 'DataInizioSellin', 'DataFineSellin',
        'ScontoExtra', 'TipoSconto1', 'TipoSconto',
        'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
    )

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=';')
    writer.writerow([
        'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
        'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
        'SelezionePromozione', 'DataInizio', 'DataFine',
        'ScontoExtra', 'TipoSconto1', 'TipoSconto',
        'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
    ])
    for r in records:
        row = list(r)
        row[7] = format_date_ddmmyyyy(row[7])   # DataInizioSellin
        row[8] = format_date_ddmmyyyy(row[8])   # DataFineSellin
        # Gold si aspetta il cumulo degli sconti in ScontoExtra (come Access)
        try:
            s1 = float(str(row[9] or '').replace(',', '.').strip() or 0)
            s2 = float(str(row[10] or '').replace(',', '.').strip() or 0)
            s3 = float(str(row[15] or '').replace(',', '.').strip() or 0)
            if s1 > 0 and (s2 > 0 or s3 > 0):
                row[9] = fmt_valore(100 - (1 - s1 / 100) * (1 - s2 / 100) * (1 - s3 / 100) * 100)
                row[10] = ''                    # TipoSconto1 vuoto: cumulo già in ScontoExtra
                row[15] = ''                    # Valore1 vuoto: già incorporato nel cumulo
            else:
                row[9] = fmt_valore(row[9])
                row[15] = fmt_valore(row[15])
        except (ValueError, TypeError):
            row[9] = fmt_valore(row[9])
            row[15] = fmt_valore(row[15])
        row[14] = fmt_valore(row[14])           # Valore
        writer.writerow(row)

    return buf.getvalue().encode('utf-8-sig'), filename


def esporta_promo_completo(username=''):
    """
    Replica EsportaCsv_Click di M_esporta.
    1. Accoda allo storico
    2. Esporta CSV Promo (se ci sono record)
    3. Esporta CSV CondAcq (se ci sono record con sconto)
    4. Svuota t_perExport
    Restituisce dict con risultati.
    """
    risultato = {
        'files': [],  # lista di (bytes, filename)
        'tot_promo': 0,
        'tot_condacq': 0,
    }

    # 1. Accoda allo storico
    accoda_storico(username)

    # 2. Salva selezione per condizioni acquisto (Q_salvaQACQ)
    PerExport.objects.filter(SelezionePromozione='').update(SelezionePromozione='1')

    # 3. Conta
    tot_tutti = PerExport.objects.count()
    tot_condacq = PerExport.objects.exclude(ScontoExtra='').exclude(ScontoExtra='0').count()

    risultato['tot_promo'] = tot_tutti
    risultato['tot_condacq'] = tot_condacq

    # 4. Export Promo
    if tot_tutti > 0:
        risultato['files'].append(esporta_promo_csv())

    # 5. Export CondAcq (dopo reset SelezionePromozione)
    if tot_condacq > 0:
        PerExport.objects.all().update(SelezionePromozione='')
        risultato['files'].append(esporta_condacq_csv())

    # 6. Svuota t_perExport
    PerExport.objects.all().delete()

    return risultato


def accoda_storico(username=''):
    """
    Replica q_AccodaExportStorico.
    Copia da t_perExport a t_perExport_Storico con data e utente.
    """
    exports = PerExport.objects.all()
    objs = []
    data_export = datetime.now().strftime('%d/%m/%Y %H:%M')

    for e in exports:
        objs.append(PerExportStorico(
            Promozioni=e.Promozioni,
            FornitoreAmministrativo=e.FornitoreAmministrativo,
            ContrattoCommerciale=e.ContrattoCommerciale,
            RagioneSociale=e.RagioneSociale,
            CodiceProdotto=e.CodiceProdotto,
            DescrizioneProdotto=e.DescrizioneProdotto,
            SelezionePromozione=e.SelezionePromozione,
            DataInizio=e.DataInizio,
            DataFine=e.DataFine,
            DataInizioSellin=e.DataInizioSellin,
            DataFineSellin=e.DataFineSellin,
            ScontoExtra=e.ScontoExtra,
            TipoSconto1=e.TipoSconto1,
            TipoSconto=e.TipoSconto,
            Meccanica=e.Meccanica,
            Meccanicav=e.Meccanicav,
            Valore=e.Valore,
            Valore1=e.Valore1,
            export=e.export,
            QtaOmaggio=e.QtaOmaggio,
            pianoB=e.pianoB,
            VL=e.vl,
            DATAEXPORT=data_export,
            utenteWind=username,
        ))

    if objs:
        PerExportStorico.objects.bulk_create(objs)

    return len(objs)


# ============================================================
# UTILITY
# ============================================================

def svuota_metterein():
    """Replica q_CancMettere_A/E/K/S."""
    MettereInA.objects.all().delete()
    MettereInE.objects.all().delete()
    MettereInK.objects.all().delete()
    MettereInS.objects.all().delete()


def conta_metterein():
    """Restituisce conteggi per la dashboard."""
    return {
        'A': MettereInA.objects.count(),
        'E': MettereInE.objects.count(),
        'K': MettereInK.objects.count(),
        'S': MettereInS.objects.count(),
    }


def conta_export():
    """Restituisce conteggi per i pulsanti export."""
    tot = PerExport.objects.count()
    condacq = PerExport.objects.exclude(ScontoExtra='').exclude(ScontoExtra='0').count()
    return {
        'tutti': tot,
        'condacq': condacq,
        'solo_promo': tot,  # In Access q_SelezionaExportCSVPromo = tutti
    }
