"""
Scarico Promo - Business Logic (services.py)
Replica la logica VBA di M_esporta e delle query Access.
"""
import csv
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


# ============================================================
# LETTURA DA GOLD (read-only, via goldreport DB)
# ============================================================

def get_gold_cursor():
    """Restituisce un cursore al database Gold (read-only)."""
    return connections['goldreport'].cursor()


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

    # 3. Genera CSV
    csv_path = esporta_aggiorna_attributi_csv()

    # 4. Conta record generati
    tot = AggiornaAttri.objects.count()

    # 5. Svuota tabelle Mettere in X
    svuota_metterein()

    return csv_path, tot


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

    # Accoda a dbo_t_chordine (articoli processabili)
    accoda_chordine()

    return non_processabili


def accoda_chordine():
    """
    Replica q_accodaDaMettereASql.
    INSERT INTO dbo_t_chordine (ccom, CodArticolo) da Mettere in A.
    """
    records = MettereInA.objects.values_list('ccom', 'codart').distinct()
    if not records:
        return 0

    with connections['goldreport'].cursor() as cursor:
        for ccom, codart in records:
            cursor.execute(
                "INSERT INTO T_chOrdine (Ccom, CodArticolo) VALUES (%s, %s)",
                [ccom, codart]
            )

    return len(records)


# ============================================================
# EXPORT CSV
# ============================================================

def esporta_aggiorna_attributi_csv():
    """
    Replica 'Esporta-AggiornaAttributi' salvato in Access.
    Genera CSV con i dati di AggiornaAttri.
    """
    timestamp = get_timestamp()
    filename = f"{timestamp}_Attr.csv"
    filepath = os.path.join(EXPORT_PATH, filename)

    records = AggiornaAttri.objects.all().values_list(
        'CodArticolo', 'ClasseAttri', 'CodAttri',
        'ValoreNum', 'ValoreAlpha', 'ValoreData',
        'dtaini', 'dtaFine'
    )

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            'Codice articolo', 'Classe attributo', 'Codice attributo',
            'Valore numerico', 'Valore alfanumerico', 'Valore data',
            'Data inizio', 'Data fine'
        ])
        for r in records:
            row = list(r)
            # Formatta data inizio
            if row[6] and hasattr(row[6], 'strftime'):
                row[6] = row[6].strftime('%d/%m/%Y')
            writer.writerow(row)

    return filepath


def esporta_promo_csv():
    """
    Replica 'Esporta-Promo'.
    Genera CSV con tutti i dati promozione da t_perExport.
    """
    timestamp = get_timestamp()
    filename = f"{timestamp}_Promo.csv"
    filepath = os.path.join(EXPORT_PATH, filename)

    records = PerExport.objects.all().values_list(
        'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
        'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
        'SelezionePromozione', 'DataInizio', 'DataFine',
        'ScontoExtra', 'TipoSconto1', 'TipoSconto',
        'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
    )

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
            'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
            'SelezionePromozione', 'DataInizio', 'DataFine',
            'ScontoExtra', 'TipoSconto1', 'TipoSconto',
            'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
        ])
        for r in records:
            writer.writerow(r)

    return filepath


def esporta_condacq_csv():
    """
    Replica 'Esporta-CondAcq'.
    Genera CSV solo per record con ScontoExtra > 0.
    """
    timestamp = get_timestamp()
    filename = f"{timestamp}_CondAcq.csv"
    filepath = os.path.join(EXPORT_PATH, filename)

    records = PerExport.objects.exclude(
        ScontoExtra=''
    ).exclude(
        ScontoExtra='0'
    ).values_list(
        'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
        'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
        'SelezionePromozione', 'DataInizio', 'DataFine',
        'ScontoExtra', 'TipoSconto1', 'TipoSconto',
        'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
    )

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            'Promozioni', 'FornitoreAmministrativo', 'ContrattoCommerciale',
            'RagioneSociale', 'CodiceProdotto', 'DescrizioneProdotto',
            'SelezionePromozione', 'DataInizio', 'DataFine',
            'ScontoExtra', 'TipoSconto1', 'TipoSconto',
            'Meccanica', 'Meccanicav', 'Valore', 'Valore1', 'vl'
        ])
        for r in records:
            writer.writerow(r)

    return filepath


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
        'promo_csv': None,
        'condacq_csv': None,
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
        risultato['promo_csv'] = esporta_promo_csv()

    # 5. Export CondAcq (dopo reset SelezionePromozione)
    if tot_condacq > 0:
        PerExport.objects.all().update(SelezionePromozione='')
        risultato['condacq_csv'] = esporta_condacq_csv()

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
    data_export = datetime.now().strftime('%d/%m/%Y')

    for e in exports:
        sel_promo = e.SelezionePromozione
        # Mid([SelezionePromozione],3,5) come in Access
        piano_b = sel_promo[2:7] if len(sel_promo) >= 7 else sel_promo[2:] if len(sel_promo) > 2 else ''

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
            ScontoExtra=e.ScontoExtra,
            TipoSconto1=e.TipoSconto1,
            TipoSconto=e.TipoSconto,
            Meccanica=e.Meccanica,
            Meccanicav=e.Meccanicav,
            Valore=e.Valore,
            Valore1=e.Valore1,
            export=e.export,
            QtaOmaggio=e.QtaOmaggio,
            pianoB=piano_b,
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
        'F': MettereInF.objects.count(),
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
