"""
Scarico Promo Reparto - Views
Flusso reparto: selezione CCOM → articoli → parametri promo → accodamento.
Ogni operazione di staging è filtrata per utente.

Funzionalità aggiuntive rispetto al modulo abbigliamento:
- Caricamento manuale articoli tramite lettore barcode (api_cerca_barcode, api_aggiungi_manuali)
- Duplicazione promozione da storico Gold (api_duplica_*)
- Date sell-in visibili nella tabella export
"""
import json
import logging
from django.utils.safestring import mark_safe
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

from .models import ArtFreFase1, ArtDaVerificare, PerExport
from .services import (
    get_ccom_list, get_piani_promo,
    carica_articoli_fase1,
    seleziona_tutti, deseleziona_tutti, toggle_selezione,
    seleziona_per_linea, seleziona_per_tipo_riordino,
    seleziona_per_fascia,
    get_linee_prodotto, get_tipi_riordino, get_fasce_prezzo,
    accoda_a_artdaverificare, verifica_duplicati,
    conferma_accodamento, svuota_fase1,
    conta_fase1, conta_export,
    get_meccaniche, get_tipi_sconto,
    cerca_articolo_barcode, aggiungi_articoli_manuali,
    get_promos_recupera, get_ccom_by_codgold,
    get_articoli_recupera, carica_da_recupera,
    importa_articoli_excel_svendita,
    piano_esiste,
)


def get_username(request):
    """Ricava lo username dell'utente corrente dalla richiesta.

    Controlla prima l'attributo 'portal_user' impostato dal middleware
    di autenticazione del portale; come fallback usa la variabile d'ambiente
    USERNAME del sistema operativo."""
    if hasattr(request, 'portal_user') and request.portal_user:
        user = request.portal_user
        if isinstance(user, dict):
            # portal_user può avere chiavi variabili a seconda del backend
            return (user.get('username') or user.get('name') or user.get('user') or 'anonymous').lower()
        return str(user).lower()
    import os
    return os.environ.get('USERNAME', 'anonymous').lower()


def _post_json(request):
    """Decodifica il corpo della richiesta POST.

    Se il Content-Type è 'application/json' effettua il parsing del body,
    altrimenti restituisce i dati standard request.POST (form encoding)."""
    if request.content_type == 'application/json':
        return json.loads(request.body)
    return request.POST


# ============================================================
# PAGINA PRINCIPALE REPARTO
# ============================================================


def reparto_home(request):
    """Vista principale del modulo Reparto.

    Carica il contesto necessario alla pagina:
    - Lista CCOM (contratti commerciali) per la dropdown
    - Piani promo disponibili
    - Articoli attualmente in staging (Fase1) per l'utente corrente
    - Meccaniche e tipi sconto per il form promozione
    """
    utente = get_username(request)
    ccom_list = get_ccom_list()
    piani = get_piani_promo()
    # Parametro opzionale in GET per pre-selezionare un CCOM
    ccom_selezionato = request.GET.get('ccom', '')

    # Recupera gli articoli in staging dell'utente, ordinati per codice articolo
    articoli_qs = ArtFreFase1.objects.filter(utente=utente).order_by('CEXR')
    # Serializza in JSON per passarli al JavaScript client-side
    articoli_json = list(articoli_qs.values(
        'id', 'SOBCEXT', 'CNUM', 'CNUF', 'DESC_CNUF',
        'ARTFO', 'CEXR', 'DESC_CEXR', 'PrezzoVOff', 'PrezzoV',
        'VL', 'STATO', 'scelta', 'LINEA_PRODOTTO', 'TIPO_RIORDINO',
    ))
    conteggi = conta_fase1(utente)
    export_counts = conta_export(modulo='reparto')

    context = {
        'username': utente,
        'ccom_list': ccom_list,
        'ccom_selezionato': ccom_selezionato,
        'piani': piani,
        'articoli': articoli_qs,
        # mark_safe necessario per non fare escaping del JSON nel template
        'articoli_json': mark_safe(json.dumps(articoli_json)),
        'conteggi': conteggi,
        'conteggi_json': mark_safe(json.dumps(conteggi)),
        'export_counts': export_counts,
        # I filtri per linea e tipo riordino vengono popolati solo se ci sono articoli
        'linee': get_linee_prodotto(utente) if articoli_qs.exists() else [],
        'tipi_riordino': get_tipi_riordino(utente) if articoli_qs.exists() else [],
        'meccaniche': get_meccaniche(),
        'tipi_sconto': get_tipi_sconto(),
    }
    return render(request, 'caricopromo_reparto/home.html', context)


# ============================================================
# API
# ============================================================


@require_POST
def api_carica_articoli(request):
    """API: carica gli articoli del CCOM indicato nella staging area (Fase1) dell'utente.

    Body JSON: { "ccom": "<codice_ccom>" }
    Risposta: articoli caricati, filtri disponibili (linee, tipi riordino, fasce prezzo).
    """
    utente = get_username(request)
    data = _post_json(request)
    ccom = data.get('ccom', '')
    if not ccom:
        return JsonResponse({'success': False, 'message': 'CCOM obbligatorio'})

    try:
        count = carica_articoli_fase1(ccom, utente)
        # Ricarica gli articoli dopo il caricamento per restituirli aggiornati
        articoli = list(ArtFreFase1.objects.filter(utente=utente).order_by('CEXR').values(
            'id', 'SOBCEXT', 'CNUM', 'CNUF', 'DESC_CNUF',
            'ARTFO', 'CEXR', 'DESC_CEXR', 'PrezzoVOff', 'PrezzoV',
            'VL', 'STATO', 'scelta', 'LINEA_PRODOTTO', 'TIPO_RIORDINO',
        ))
        return JsonResponse({
            'success': True, 'count': count,
            'articoli': articoli,
            'linee': get_linee_prodotto(utente),
            'tipi_riordino': get_tipi_riordino(utente),
            'fasce_prezzo': get_fasce_prezzo(utente),
            'message': f'{count} articoli caricati',
        })
    except Exception as e:
        logger.exception('carica_articoli_fase1 fallito: ccom=%s utente=%s', ccom, utente)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



@require_POST
def api_toggle_selezione(request):
    """API: inverte lo stato di selezione di un singolo articolo in staging.

    Body JSON: { "id": <id_articolo> }
    Risposta: nuovo stato 'scelta' e conteggi aggiornati.
    """
    utente = get_username(request)
    data = _post_json(request)
    art_id = data.get('id')
    if not art_id:
        return JsonResponse({'success': False})

    nuovo_stato = toggle_selezione(int(art_id), utente)
    return JsonResponse({
        'success': True, 'scelta': nuovo_stato,
        'conteggi': conta_fase1(utente),
    })



@require_POST
def api_seleziona_batch(request):
    """API: operazioni di selezione/deselezione in blocco sulla staging area.

    Body JSON: { "azione": "<tutti|nessuno|linea|tipo_riordino|fascia>", "filtro": "<valore>" }
    Le azioni 'linea', 'tipo_riordino' e 'fascia' richiedono il campo 'filtro'.
    Risposta: stato di selezione di tutti gli articoli e conteggi aggiornati.
    """
    utente = get_username(request)
    data = _post_json(request)
    azione = data.get('azione', '')
    filtro_val = data.get('filtro', '')

    # Esegue l'azione richiesta sulla staging area dell'utente
    if azione == 'tutti':
        seleziona_tutti(utente)
    elif azione == 'nessuno':
        deseleziona_tutti(utente)
    elif azione == 'linea' and filtro_val:
        seleziona_per_linea(filtro_val, utente)
    elif azione == 'tipo_riordino' and filtro_val:
        seleziona_per_tipo_riordino(filtro_val, utente)
    elif azione == 'fascia' and filtro_val:
        seleziona_per_fascia(filtro_val, utente)

    # Restituisce lo stato aggiornato di tutti gli articoli per sincronizzare l'UI
    articoli_stato = list(
        ArtFreFase1.objects.filter(utente=utente).order_by('CEXR').values('id', 'scelta')
    )
    return JsonResponse({
        'success': True,
        'conteggi': conta_fase1(utente),
        'articoli_stato': articoli_stato,
    })



@require_POST
def api_accoda_promo(request):
    """API: accoda gli articoli selezionati alla promozione con i parametri indicati.

    Body JSON: dizionario con tutti i parametri della promozione
    (selezione_promo, date sell-out/sell-in, sconti, meccanica, ecc.).

    Gestisce il caso di articoli duplicati: se presenti e non si forza
    l'inserimento, restituisce 'richiedi_conferma: True' con la lista duplicati.
    """
    utente = get_username(request)
    data = _post_json(request)

    # Raccoglie tutti i parametri promo dal body della richiesta
    params = {
        'selezione_promo': data.get('selezione_promo', ''),
        'data_inizio': data.get('data_inizio', ''),
        'data_fine': data.get('data_fine', ''),
        'sellin_inizio': data.get('sellin_inizio', ''),
        'sellin_fine': data.get('sellin_fine', ''),
        'sconto_extra': data.get('sconto_extra', ''),
        'sconto1': data.get('sconto1', ''),
        'sconto2': data.get('sconto2', ''),
        'tipo_sconto': data.get('tipo_sconto', ''),
        'meccanica': data.get('meccanica', ''),
        'meccanicav': data.get('meccanicav', ''),
        'valore': data.get('valore', ''),
        'valore1': data.get('valore1', ''),
        'qta_omaggio': data.get('qta_omaggio', ''),
    }

    # Le date sell-in sono obbligatorie per procedere con l'accodamento
    if not params['sellin_inizio'] or not params['sellin_fine']:
        return JsonResponse({'success': False, 'message': 'Date Sell-in obbligatorie'})

    # Verifica che il piano selezionato esista davvero su Gold in questo momento:
    # evita di accodare/esportare promozioni legate a piani non reali/autorizzati
    # (es. piani di prova mai pianificati ufficialmente).
    piano_codice = data.get('piano_codice', '')
    if not piano_esiste(piano_codice):
        return JsonResponse({
            'success': False,
            'message': f'Il Piano Promo "{piano_codice}" non risulta presente su Gold: verifica di averlo selezionato correttamente.',
        })

    # Verifica che ci siano articoli selezionati prima di procedere
    selezionati = ArtFreFase1.objects.filter(utente=utente, scelta=True).count()
    if selezionati == 0:
        return JsonResponse({'success': False, 'message': 'Nessun articolo selezionato'})

    valore_da_offerta = bool(data.get('valore_da_offerta', False))

    try:
        _, senza_prezzo = accoda_a_artdaverificare(params, utente, fallback_prezzo=valore_da_offerta)

        # Se "Usa Prz. Offerta" è attivo e tutti gli articoli selezionati mancano del prezzo, blocca
        if valore_da_offerta and not ArtDaVerificare.objects.filter(utente=utente).exists():
            return JsonResponse({
                'success': False,
                'message': 'Nessun articolo accodato: tutti gli articoli selezionati sono privi di Prezzo Offerta.',
                'senza_prezzo': senza_prezzo,
            })

        duplicati = verifica_duplicati(utente, modulo='reparto')

        # Se ci sono duplicati e l'utente non ha forzato, chiede conferma
        if duplicati and not data.get('forza', False):
            return JsonResponse({
                'success': False,
                'duplicati': duplicati,
                'count_duplicati': len(duplicati),
                'message': f'{len(duplicati)} articoli già presenti. Vuoi accodare comunque?',
                'richiedi_conferma': True,
                'senza_prezzo': senza_prezzo,
            })

        # Conferma definitiva: sposta gli articoli nella tabella export
        operatore = data.get('operatore', '') or utente
        count = conferma_accodamento(utente, modulo='reparto', operatore=operatore)
        deseleziona_tutti(utente)

        return JsonResponse({
            'success': True, 'count': count,
            'export_counts': conta_export(modulo='reparto'),
            'message': f'{count} articoli accodati alla promozione',
            'senza_prezzo': senza_prezzo,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



@require_POST
def api_svuota_fase1(request):
    """API: svuota la staging area (Fase1) dell'utente corrente.
    Tutti gli articoli caricati vengono rimossi senza conferma ulteriore."""
    utente = get_username(request)
    svuota_fase1(utente)
    return JsonResponse({
        'success': True,
        'conteggi': conta_fase1(utente),
        'message': 'Articoli svuotati',
    })



@require_POST
def api_importa_excel_svendita(request):
    """API: importa articoli da file Excel svendita (Codice, Descrizione, Prezzo svendita)."""
    utente = get_username(request)
    excel_file = request.FILES.get('file')
    if not excel_file:
        return JsonResponse({'success': False, 'message': 'Nessun file inviato'}, status=400)
    try:
        count, incompleti = importa_articoli_excel_svendita(excel_file, utente)
        articoli = list(ArtFreFase1.objects.filter(utente=utente).order_by('CEXR').values(
            'id', 'SOBCEXT', 'CNUM', 'CNUF', 'DESC_CNUF',
            'ARTFO', 'CEXR', 'DESC_CEXR', 'PrezzoVOff', 'PrezzoV',
            'VL', 'STATO', 'scelta', 'LINEA_PRODOTTO', 'TIPO_RIORDINO',
        ))
        return JsonResponse({
            'success': True,
            'count': count,
            'articoli': articoli,
            'conteggi': conta_fase1(utente),
            'incompleti': incompleti,
            'message': f'{count} articoli importati da Excel',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


def api_cerca_barcode(request):
    """API (GET): ricerca un articolo per codice barcode/EAN o codice articolo.

    Query param: barcode=<valore>
    Risposta: { found: bool, articolo: {...} } oppure { found: false, message: "..." }
    """
    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'found': False, 'message': 'Barcode vuoto'})
    try:
        articolo = cerca_articolo_barcode(barcode)
    except Exception as e:
        return JsonResponse({'found': False, 'message': str(e)}, status=500)
    if not articolo:
        return JsonResponse({'found': False, 'message': f'Articolo non trovato: {barcode}'})
    return JsonResponse({'found': True, 'articolo': articolo})



@require_POST
def api_aggiungi_manuali(request):
    """API: aggiunge alla staging area una lista di articoli inseriti manualmente.

    Body JSON: { "articoli": [ {...}, {...} ] }
    Ogni articolo deve avere almeno i campi CEXR, DESC_CEXR, CNUM, ecc.
    Risposta: articoli aggiornati in staging e conteggi.
    """
    utente = get_username(request)
    data = _post_json(request)
    articoli = data.get('articoli', [])
    if not articoli:
        return JsonResponse({'success': False, 'message': 'Nessun articolo da aggiungere'})

    try:
        count = aggiungi_articoli_manuali(articoli, utente)
        articoli_fase1 = list(ArtFreFase1.objects.filter(utente=utente).order_by('CEXR').values(
            'id', 'SOBCEXT', 'CNUM', 'CNUF', 'DESC_CNUF',
            'ARTFO', 'CEXR', 'DESC_CEXR', 'PrezzoVOff', 'PrezzoV',
            'VL', 'STATO', 'scelta', 'LINEA_PRODOTTO', 'TIPO_RIORDINO',
        ))
        return JsonResponse({
            'success': True,
            'count': count,
            'articoli': articoli_fase1,
            'conteggi': conta_fase1(utente),
            'message': f'{count} articoli aggiunti',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



def api_visualizza_inseriti(request):
    """API (GET): restituisce tutti gli articoli in PerExport per il modulo reparto.

    Aggiunge il flag 'mine' (True/False) per distinguere le righe dell'utente
    corrente da quelle inserite da altri operatori. Solo le righe 'mine' possono
    essere rimosse; le altre sono visibili in sola lettura.
    """
    utente = get_username(request)
    articoli = list(PerExport.objects.filter(utenteWind='reparto')
                    .order_by('pianoB', 'CodiceProdotto').values(
        'id', 'CodiceProdotto', 'DescrizioneProdotto', 'FornitoreAmministrativo',
        'SelezionePromozione', 'DataInizio', 'DataFine',
        'DataInizioSellin', 'DataFineSellin',
        'ScontoExtra', 'TipoSconto', 'TipoSconto1', 'Valore1',
        'Meccanica', 'vl', 'Valore', 'DATAEXPORT', 'pianoB',
    ))
    prezzi_off = dict(ArtFreFase1.objects.values_list('CEXR', 'PrezzoVOff'))
    for a in articoli:
        a['PrezzoVOff'] = prezzi_off.get(a['CodiceProdotto'], '')
        a['mine'] = (a['pianoB'] == utente)
    return JsonResponse({'articoli': articoli})



@require_POST
def api_svuota_inseriti(request):
    """API: rimuove dalla tabella export tutti gli articoli inseriti dall'utente corrente."""
    utente = get_username(request)
    PerExport.objects.filter(utenteWind='reparto', pianoB=utente).delete()
    return JsonResponse({'success': True, 'message': 'I tuoi articoli sono stati rimossi dall\'export'})


@require_POST
def api_rimuovi_inserito(request):
    """API: rimuove un singolo articolo dalla tabella export, solo se appartiene all'utente corrente."""
    utente = get_username(request)
    data = _post_json(request)
    art_id = data.get('id')
    if not art_id:
        return JsonResponse({'success': False, 'message': 'ID mancante'}, status=400)
    deleted, _ = PerExport.objects.filter(id=art_id, utenteWind='reparto', pianoB=utente).delete()
    if not deleted:
        return JsonResponse({'success': False, 'message': 'Articolo non trovato o non di tua proprietà'}, status=404)
    return JsonResponse({'success': True})


# ============================================================
# DUPLICA PROMO DA STORICO GOLD
# Permette di copiare gli articoli di una promozione passata
# (recuperata dal database Gold) nella staging area corrente.
# ============================================================


def api_duplica_get_promos(request):
    """API (GET): restituisce l'elenco delle promozioni storiche disponibili
    per la funzione "Duplica da Promo Gold"."""
    try:
        promos = get_promos_recupera()
        return JsonResponse({'success': True, 'promos': promos})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



def api_duplica_get_ccom(request):
    """API (GET): dato un codice Gold (CODGOLD), restituisce i CCOM (fornitori)
    associati a quella promozione storica.

    Query param: codgold=<valore>
    """
    codgold = request.GET.get('codgold', '').strip()
    if not codgold:
        return JsonResponse({'success': False, 'message': 'codgold mancante'}, status=400)
    try:
        ccoms = get_ccom_by_codgold(codgold)
        return JsonResponse({'success': True, 'ccoms': ccoms})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



def api_duplica_get_articoli(request):
    """API (GET): restituisce la lista degli articoli di una promo storica
    filtrata per CODGOLD e CCOM (o tutti i fornitori con '__TUTTI__').

    Query params: codgold=<valore>&ccom=<valore>
    """
    codgold = request.GET.get('codgold', '').strip()
    ccom = request.GET.get('ccom', '').strip()
    if not codgold or not ccom:
        return JsonResponse({'success': False, 'message': 'parametri mancanti'}, status=400)
    try:
        articoli = get_articoli_recupera(codgold, ccom)
        return JsonResponse({'success': True, 'articoli': articoli})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



@require_POST
def api_duplica_inserisci(request):
    """API: carica nella staging area dell'utente gli articoli di una promo storica.

    Body JSON: { "codgold": "<codice>", "ccom": "<ccom>" }
    Risposta: articoli caricati e conteggi aggiornati.
    """
    utente = get_username(request)
    # Supporta sia JSON che form-data per retrocompatibilità
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    codgold = str(data.get('codgold', '')).strip()
    ccom = str(data.get('ccom', '')).strip()
    if not codgold or not ccom:
        return JsonResponse({'success': False, 'message': 'Seleziona promo e CCOM'}, status=400)
    try:
        count = carica_da_recupera(codgold, ccom, utente)
        articoli_fase1 = list(ArtFreFase1.objects.filter(utente=utente).values(
            'id', 'SOBCEXT', 'CNUM', 'CNUF', 'DESC_CNUF',
            'ARTFO', 'CEXR', 'DESC_CEXR', 'PrezzoVOff', 'PrezzoV',
            'VL', 'STATO', 'scelta', 'LINEA_PRODOTTO', 'TIPO_RIORDINO',
        ))
        return JsonResponse({
            'success': True,
            'count': count,
            'articoli': articoli_fase1,
            'conteggi': conta_fase1(utente),
            'message': f'{count} articoli caricati da promo duplicata',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
