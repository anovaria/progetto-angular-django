"""
Scarico Promo - Views
Gestisce le interfacce web che replicano M_esporta e m_MettereX.

Questo modulo riproduce la logica dell'applicazione Access originale per
la gestione delle promozioni. Le viste principali sono:
- dashboard: equivalente a M_esporta, con conteggi e azioni di export.
- mettere_in: equivalente a m_MettereA/E/F/K, per inserire articoli nelle
  tabelle di staging 'Mettere in X' (stati A, E, F, I, K, S).
- azione_valida_a: valida gli articoli in A e genera il report non posso.
- azione_crea_attributi: crea il file CSV per l'import attributi su Gold.
- azione_esporta_csv: esporta le promozioni in CSV (Promo + CondAcq).
"""
import io
import json
import zipfile
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    MettereInA, MettereInE, MettereInF, MettereInI, MettereInK, MettereInS,
    PerExport, PerExportStorico, NonPossoMettereInA,
)
from .services import (
    conta_metterein, conta_export,
    valida_mettere_in_a, elabora_attributi, esporta_promo_completo,
    verifica_codart, verifica_ccom, carica_articoli_da_ccom,
    get_descrizioni_bulk,
)
from modules.caricopromo_reparto.services import get_ccom_list


def get_username(request):
    """
    Recupera il nome utente dall'oggetto request.
    Supporta sia l'attributo portal_user (middleware personalizzato)
    sia la variabile d'ambiente USERNAME come fallback per ambienti locali.
    """
    if hasattr(request, 'portal_user') and request.portal_user:
        user = request.portal_user
        if isinstance(user, dict):
            return (user.get('username') or user.get('name') or user.get('user') or 'anonymous').lower()
        return str(user).lower()
    import os
    return os.environ.get('USERNAME', 'anonymous').lower()


# ============================================================
# DASHBOARD (replica M_esporta)
# ============================================================

def storico(request):
    """
    Mostra lo storico degli export CSV effettuati, raggruppati per sessione (data + utente).
    """
    from django.db.models import Max
    from collections import defaultdict

    limit = min(int(request.GET.get('limit', 20)), 200)
    filtro_utente = request.GET.get('utente', '').strip()

    qs = PerExportStorico.objects.all()
    if filtro_utente:
        qs = qs.filter(utenteWind__icontains=filtro_utente)

    # Sessioni più recenti (N distinte data+utente, ordinate per id decrescente)
    sessioni_keys = list(
        qs.values('DATAEXPORT', 'utenteWind')
          .annotate(max_id=Max('id'))
          .order_by('-max_id')[:limit]
    )

    sessioni = []
    if sessioni_keys:
        from django.db.models import Q
        q = Q()
        for s in sessioni_keys:
            q |= Q(DATAEXPORT=s['DATAEXPORT'], utenteWind=s['utenteWind'])

        grouped = defaultdict(list)
        for r in qs.filter(q).order_by('-id'):
            grouped[(r.DATAEXPORT, r.utenteWind)].append(r)

        for s in sessioni_keys:
            articoli = grouped.get((s['DATAEXPORT'], s['utenteWind']), [])
            inseritori = list(dict.fromkeys(a.pianoB for a in articoli if a.pianoB))
            sessioni.append({
                'data': s['DATAEXPORT'],
                'utente': s['utenteWind'],
                'tot': len(articoli),
                'articoli': articoli,
                'inseritori': inseritori,
            })

    context = {
        'sessioni': sessioni,
        'limit': limit,
        'filtro_utente': filtro_utente,
        'tot_sessioni': len(sessioni),
    }
    return render(request, 'scaricopromo/storico.html', context)


def attributi(request):
    """
    Pagina Imposta Attributi: gestione tabelle MettereIn* e generazione file CSV per Gold.
    """
    conteggi = conta_metterein()
    context = {
        'conteggi': conteggi,
        'can_crea_attributi': any(v > 0 for v in conteggi.values()),
    }
    return render(request, 'scaricopromo/attributi.html', context)


def dashboard(request):
    """
    Pagina principale - replica M_esporta dell'applicazione Access.
    Mostra:
    - Griglia con conteggi per ogni stato "Mettere in X" (A/E/F/I/K/S),
      cliccabili per aprire il form di gestione.
    - Statistiche degli articoli pronti per l'esportazione (PerExport).
    - Tabella promozioni (equivalente alla submaschera sm_Esporta).
    - Pulsanti azione: Crea Attributi e Esporta CSV.
    """
    export_counts = conta_export()
    promozioni = PerExport.objects.all().order_by('DataInizio', 'CodiceProdotto')

    context = {
        'export_counts': export_counts,
        'promozioni': promozioni,
        'can_export_csv': export_counts['tutti'] > 0,
    }
    return render(request, 'scaricopromo/dashboard.html', context)


# ============================================================
# GESTIONE "METTERE IN X" (replica m_MettereA/E/F/K)
# ============================================================

def mettere_in(request, stato):
    """
    Form per inserire codici articolo nelle tabelle 'Mettere in X'.
    Supporta tre modalità di inserimento:
    1. Singolo: inserimento manuale con verifica real-time via AJAX.
    2. Bulk CCOM: carica tutti gli articoli di un CCOM (solo stati A e I).
    3. Incolla Excel: inserimento massivo da testo copiato da Excel.

    GET: mostra il form con la lista degli articoli già inseriti.
    POST (singolo): verifica il codice e aggiunge l'articolo.

    Il parametro 'stato' identifica la tabella destinazione (A/E/F/I/K/S).
    has_ccom=True abilita il pannello di caricamento per CCOM (solo A e I).
    """
    model_map = {
        'A': MettereInA, 'E': MettereInE, 'F': MettereInF,
        'I': MettereInI, 'K': MettereInK, 'S': MettereInS,
    }
    model = model_map.get(stato.upper())
    if not model:
        return HttpResponse("Stato non valido", status=400)

    # Il caricamento per CCOM è disponibile solo per gli stati A e I
    has_ccom = stato.upper() in ('A', 'I')

    if request.method == 'POST':
        codart = request.POST.get('codart', '').strip()

        if codart:
            verifica = verifica_codart(codart)
            if not verifica['found']:
                # Ricarica la pagina con messaggio di errore se il codice non esiste
                articoli = model.objects.all()
                codarts = [a.codart for a in articoli]
                descrizioni = get_descrizioni_bulk(codarts)
                articoli_list = [
                    {'pk': a.pk, 'codart': a.codart,
                     'ccom': getattr(a, 'ccom', ''),
                     'descrizione': descrizioni.get(a.codart, '')}
                    for a in articoli
                ]
                context = {
                    'stato': stato.upper(), 'articoli': articoli_list,
                    'has_ccom': has_ccom, 'count': len(articoli_list),
                    'conteggi': conta_metterein(),
                    'errore_codart': verifica.get('message', 'Codice articolo non trovato'),
                    'codart_input': codart,
                }
                return render(request, 'scaricopromo/mettere_in.html', context)
            # usa il CODART canonico (in caso di input EAN, restituisce il codice articolo)
            codart = verifica['codart']
            model.objects.create(codart=codart)

        return redirect('scaricopromo:mettere_in', stato=stato)

    # GET: carica la lista articoli arricchita con le descrizioni
    articoli = model.objects.all()
    codarts = [a.codart for a in articoli]
    descrizioni = get_descrizioni_bulk(codarts)
    articoli_list = [
        {'pk': a.pk, 'codart': a.codart,
         'ccom': getattr(a, 'ccom', ''),
         'descrizione': descrizioni.get(a.codart, '')}
        for a in articoli
    ]
    conteggi = conta_metterein()

    context = {
        'stato': stato.upper(),
        'articoli': articoli_list,
        'has_ccom': has_ccom,
        'count': len(articoli_list),
        'conteggi': conteggi,
        # La lista CCOM viene caricata solo se necessaria (stati A e I)
        'ccom_list': get_ccom_list() if has_ccom else [],
    }
    return render(request, 'scaricopromo/mettere_in.html', context)


@require_POST
def elimina_articolo(request, stato, pk):
    """Elimina un articolo dalla tabella 'Mettere in X' specificata dallo stato."""
    model_map = {
        'A': MettereInA, 'E': MettereInE, 'F': MettereInF,
        'I': MettereInI, 'K': MettereInK, 'S': MettereInS,
    }
    model = model_map.get(stato.upper())
    if model:
        model.objects.filter(pk=pk).delete()
    return redirect('scaricopromo:mettere_in', stato=stato)


# ============================================================
# AZIONI (replica pulsanti M_esporta)
# ============================================================

@require_POST
def azione_valida_a(request):
    """
    Replica Comando3_Click di m_MettereA.
    Valida gli articoli presenti in MettereInA:
    - Gli articoli elaborabili vengono accodati agli ordini.
    - Gli articoli non elaborabili (es. già presenti, giacenza errata)
      vengono spostati in NonPossoMettereInA per gestione manuale.

    Restituisce JSON con lista dei non processabili e il messaggio di esito.
    """
    non_processabili = valida_mettere_in_a()
    conteggi = conta_metterein()

    return JsonResponse({
        'success': True,
        'non_processabili': non_processabili,
        'has_warnings': len(non_processabili) > 0,
        'message': (
            f"Ci sono {len(non_processabili)} articoli da gestire manualmente!"
            if non_processabili
            else "Tutti gli articoli sono stati elaborati"
        ),
        'conteggi': conteggi,
    })


@require_POST
def azione_crea_attributi(request):
    """
    Replica Comando15_Click di M_esporta.
    Elabora tutti gli attributi dalle tabelle MettereIn* e genera
    un file CSV pronto per l'import su Gold (gestione attributi promo).
    Restituisce il CSV come download diretto; in caso di errore restituisce JSON.
    """
    try:
        csv_content, csv_filename, tot_records = elabora_attributi()
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{csv_filename}"'
        # Header custom per indicare al client il totale record elaborati
        response['X-Tot-Records'] = str(tot_records)
        return response
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Errore: {str(e)}",
        }, status=500)


@require_POST
def azione_esporta_csv(request):
    """
    Replica EsportaCsv_Click di M_esporta.
    Esporta le promozioni dalla tabella PerExport in formato CSV.
    Genera due file distinti: Promo e CondAcq (condizioni acquisto).
    Se sono presenti entrambi i file, li comprime in un unico ZIP.
    Se è presente solo un file, lo restituisce direttamente come CSV.
    """
    username = get_username(request)

    try:
        risultato = esporta_promo_completo(username)
        files = risultato['files']

        if not files:
            return JsonResponse({'success': False, 'message': 'Nessun record da esportare.'}, status=400)

        if len(files) == 1:
            # Un solo file: risposta CSV diretta
            content, filename = files[0]
            response = HttpResponse(content, content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            # Più file: compressione in ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for content, filename in files:
                    zf.writestr(filename, content)
            zip_buf.seek(0)
            # Usa il timestamp del primo file come prefisso del nome ZIP
            timestamp = files[0][1].split('_')[0]
            response = HttpResponse(zip_buf.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{timestamp}_Promo.zip"'

        return response
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Errore: {str(e)}",
        }, status=500)


# ============================================================
# REPORT "NON POSSO METTERE IN A"
# ============================================================

def report_non_posso(request):
    """
    Replica R_NonpossomettereA dell'applicazione Access.
    Mostra l'elenco degli articoli presenti in NonPossoMettereInA,
    arricchito con i dati di giacenza letti dalla tabella t_ArticoliGiacTutti
    di GoldReport tramite query diretta (JOIN non disponibile tra i due DB).
    Questi articoli devono essere gestiti manualmente dall'operatore.
    """
    articoli = NonPossoMettereInA.objects.all()

    # Arricchisci con dati giacenza da Gold (query diretta perché DB diverso)
    codici = list(articoli.values_list('codart', flat=True))
    giacenze = {}

    if codici:
        from django.db import connections
        placeholders = ','.join(['%s'] * len(codici))
        sql = f"""
            SELECT CODARTICOLO, STATO, GIAC_PDV, GIAC_DEP
            FROM t_ArticoliGiacTutti
            WHERE CODARTICOLO IN ({placeholders})
        """
        with connections['goldreport'].cursor() as cursor:
            cursor.execute(sql, codici)
            for row in cursor.fetchall():
                giacenze[row[0]] = {
                    'stato': row[1],
                    'giac_pdv': row[2],
                    'giac_dep': row[3],
                }

    # Combina i dati del modello con le giacenze dal DB
    report_data = []
    for art in articoli:
        giac = giacenze.get(art.codart, {})
        report_data.append({
            'ccom': art.ccom,
            'codart': art.codart,
            'stato': giac.get('stato', ''),
            'giac_pdv': giac.get('giac_pdv', 0),
            'giac_dep': giac.get('giac_dep', 0),
        })

    context = {
        'report_data': report_data,
        'titolo': 'Elenco articoli con Giacenza che non posso mettere in A',
        'sottotitolo': 'I seguenti articoli vanno gestiti manualmente',
    }
    return render(request, 'scaricopromo/report_non_posso.html', context)


# ============================================================
# API CONTEGGI (per aggiornamento AJAX dashboard)
# ============================================================

def api_conteggi(request):
    """
    Restituisce i conteggi aggiornati per la dashboard via AJAX.
    Chiamata periodicamente dal frontend per aggiornare i badge
    senza ricaricare la pagina.
    """
    conteggi = conta_metterein()
    export_counts = conta_export()
    return JsonResponse({
        'conteggi': conteggi,
        'export': export_counts,
    })


@csrf_exempt
def api_verifica_codart(request):
    """
    Verifica l'esistenza di un codice articolo (o EAN) in GoldReport.
    Usata via AJAX dalla funzione onCodartInput() del template mettere_in.html
    per validare il codice prima di abilitare il pulsante Aggiungi.
    Restituisce JSON {found: bool, codart: str, descrizione: str, message: str}.
    """
    codart = request.GET.get('codart', '').strip()
    if not codart:
        return JsonResponse({'found': False, 'message': 'Codice vuoto'})
    try:
        result = verifica_codart(codart)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'found': False, 'message': str(e)}, status=500)


@csrf_exempt
def api_verifica_ccom(request):
    """
    Verifica l'esistenza di un CCOM nella tabella t_artfrepromo di GoldReport.
    Usata via AJAX prima di abilitare il pulsante "Carica articoli CCOM".
    """
    ccom = request.GET.get('ccom', '').strip()
    if not ccom:
        return JsonResponse({'found': False, 'message': 'CCOM vuoto'})
    try:
        result = verifica_ccom(ccom)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'found': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def api_carica_da_ccom(request, stato):
    """
    Carica tutti gli articoli di un CCOM nella tabella MettereInX indicata.
    Gli articoli già presenti vengono ignorati (nessun duplicato).
    Restituisce JSON con conteggio articoli aggiunti e lista aggiornata.
    Disponibile solo per gli stati A e I (has_ccom nel template).
    """
    model_map = {
        'A': MettereInA, 'E': MettereInE, 'F': MettereInF,
        'I': MettereInI, 'K': MettereInK, 'S': MettereInS,
    }
    model = model_map.get(stato.upper())
    if not model:
        return JsonResponse({'success': False, 'message': 'Stato non valido'})

    import json as _json
    try:
        data = _json.loads(request.body)
    except Exception:
        data = request.POST
    ccom = data.get('ccom', '').strip()
    if not ccom:
        return JsonResponse({'success': False, 'message': 'CCOM obbligatorio'})

    try:
        count = carica_articoli_da_ccom(ccom, model)
        articoli = list(model.objects.values('id', 'codart', 'ccom'))
        return JsonResponse({
            'success': True,
            'count': count,
            'articoli': articoli,
            'message': f'{count} articoli aggiunti per CCOM {ccom}' if count else 'Nessun articolo nuovo (già tutti presenti)',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def api_incolla_codici(request, stato):
    """
    Inserimento massivo da incolla Excel.
    Riceve una stringa di testo (testo) con un codice per riga (separatori: \\n, \\r, \\t).
    Per ogni codice:
    - Verifica l'esistenza tramite verifica_codart (supporta EAN).
    - Controlla se già presente nella tabella (evita duplicati).
    - Inserisce i codici validi e non duplicati.

    Restituisce statistiche su inseriti, non trovati e duplicati.
    """
    model_map = {
        'A': MettereInA, 'E': MettereInE, 'F': MettereInF,
        'I': MettereInI, 'K': MettereInK, 'S': MettereInS,
    }
    model = model_map.get(stato.upper())
    if not model:
        return JsonResponse({'success': False, 'message': 'Stato non valido'})

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    testo = data.get('testo', '')

    # Normalizza i separatori di riga e filtra le righe vuote
    righe = [r.strip() for r in testo.replace('\r', '\n').split('\n') if r.strip()]
    if not righe:
        return JsonResponse({'success': False, 'message': 'Nessun codice incollato'})

    # Precarica i codici già presenti per evitare query per ogni riga
    esistenti = set(model.objects.values_list('codart', flat=True))
    inseriti, non_trovati, duplicati = [], [], []

    for codice in righe:
        verifica = verifica_codart(codice)
        if not verifica['found']:
            non_trovati.append(codice)
            continue
        codart = verifica['codart']
        if codart in esistenti:
            duplicati.append(codart)
            continue
        model.objects.create(codart=codart)
        esistenti.add(codart)
        inseriti.append(codart)

    return JsonResponse({
        'success': True,
        'inseriti': len(inseriti),
        'non_trovati': non_trovati,
        'duplicati': len(duplicati),
        'message': f'{len(inseriti)} inseriti, {len(non_trovati)} non trovati, {len(duplicati)} già presenti',
    })
