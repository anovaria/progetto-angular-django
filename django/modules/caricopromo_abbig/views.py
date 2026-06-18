"""
Scarico Promo Abbigliamento - Views
Riusa la logica del reparto, cambia solo il template.

Questo modulo gestisce il flusso di caricamento promozioni per il reparto
Abbigliamento. La struttura è analoga a caricopromo_reparto, ma utilizza
il template dedicato 'caricopromo_abbig/home.html' e non include le
funzionalità di duplicazione promo da storico Gold né il caricamento barcode.

Flusso principale:
1. abbig_home       — pagina principale con griglia articoli e form promo
2. api_carica_articoli — carica gli articoli di un CCOM in staging (Fase1)
3. api_toggle_selezione / api_seleziona_batch — gestione selezione articoli
4. api_accoda_promo — accoda gli articoli selezionati alla promozione
5. api_svuota_fase1 — svuota la staging area dell'utente
6. api_visualizza_inseriti / api_svuota_inseriti — gestione export promo
7. api_importa_excel — importa articoli da file Excel fornitore
"""
import json
from django.utils.safestring import mark_safe
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from modules.caricopromo_reparto.models import ArtFreFase1, PerExport
from modules.caricopromo_reparto.services import (
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
    importa_articoli_excel,
    piano_esiste,
)


def get_username(request):
    """Ricava lo username dell'utente corrente dalla richiesta.

    Controlla prima l'attributo 'portal_user' (impostato dal middleware
    di autenticazione del portale), poi come fallback legge la variabile
    d'ambiente USERNAME del sistema operativo."""
    if hasattr(request, 'portal_user') and request.portal_user:
        user = request.portal_user
        if isinstance(user, dict):
            # portal_user può essere un dizionario con chiavi variabili
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



def abbig_home(request):
    """Vista principale del modulo Abbigliamento.

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
    export_counts = conta_export(modulo='abbig')

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
    return render(request, 'caricopromo_abbig/home.html', context)



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
    # evita di accodare/esportare promozioni legate a piani non reali/autorizzati.
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

    try:
        # Accoda in tabella temporanea di verifica; fallback_prezzo=True per abbigliamento
        accoda_a_artdaverificare(params, utente, fallback_prezzo=True)
        duplicati = verifica_duplicati(utente, modulo='abbig')

        # Se ci sono duplicati e l'utente non ha forzato, chiede conferma
        if duplicati and not data.get('forza', False):
            return JsonResponse({
                'success': False,
                'duplicati': duplicati,
                'count_duplicati': len(duplicati),
                'message': f'{len(duplicati)} articoli già presenti. Vuoi accodare comunque?',
                'richiedi_conferma': True,
            })

        # Conferma definitiva: sposta gli articoli nella tabella export
        operatore = data.get('operatore', '') or utente
        count = conferma_accodamento(utente, modulo='abbig', operatore=operatore)
        deseleziona_tutti(utente)

        return JsonResponse({
            'success': True, 'count': count,
            'export_counts': conta_export(modulo='abbig'),
            'message': f'{count} articoli accodati alla promozione',
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



def api_visualizza_inseriti(request):
    """API (GET): restituisce tutti gli articoli presenti nella tabella export (PerExport).

    Arricchisce ogni articolo con il prezzo di vendita corrente (PrezzoV)
    recuperato dalla staging area per corrispondenza del codice articolo.
    """
    articoli = list(PerExport.objects.filter(utenteWind='abbig').order_by('CodiceProdotto').values(
        'CodiceProdotto', 'DescrizioneProdotto', 'FornitoreAmministrativo',
        'SelezionePromozione', 'DataInizio', 'DataFine',
        'TipoSconto', 'ScontoExtra', 'TipoSconto1', 'Valore1',
        'Meccanica', 'vl', 'Valore', 'DATAEXPORT', 'pianoB',
    ))
    # Dizionario {CEXR: PrezzoV} per join in Python senza query aggiuntive
    prezzi_vend = dict(
        ArtFreFase1.objects.values_list('CEXR', 'PrezzoV')
    )
    for a in articoli:
        a['PrezzoV'] = prezzi_vend.get(a['CodiceProdotto'], '')
    return JsonResponse({'articoli': articoli})



@require_POST
def api_svuota_inseriti(request):
    """API: svuota gli articoli del modulo abbigliamento dalla tabella export (PerExport)."""
    PerExport.objects.filter(utenteWind='abbig').delete()
    return JsonResponse({'success': True, 'message': 'Articoli export svuotati'})



@require_POST
def api_importa_excel(request):
    """API: importa articoli da un file Excel del fornitore nella staging area (Fase1).

    Richiede un file multipart con chiave 'file' (.xlsx o .xls).
    Le colonne necessarie nel file sono:
    CODART, DESCRART, CODFORN, CCOM, DESCRCCOM, pv_std, PVOFF ARR
    """
    utente = get_username(request)
    excel_file = request.FILES.get('file')
    if not excel_file:
        return JsonResponse({'success': False, 'message': 'Nessun file allegato'})

    try:
        count = importa_articoli_excel(excel_file, utente)
        print(f"[api_importa_excel] count={count}, utente={utente}")
        # Ricarica gli articoli aggiornati dopo l'importazione
        articoli = list(ArtFreFase1.objects.filter(utente=utente).order_by('CEXR').values(
            'id', 'SOBCEXT', 'CNUM', 'CNUF', 'DESC_CNUF',
            'ARTFO', 'CEXR', 'DESC_CEXR', 'PrezzoVOff', 'PrezzoV',
            'VL', 'STATO', 'scelta', 'LINEA_PRODOTTO', 'TIPO_RIORDINO',
        ))
        print(f"[api_importa_excel] articoli in DB dopo import: {len(articoli)}")
        return JsonResponse({
            'success': True, 'count': count,
            'articoli': articoli,
            'linee': get_linee_prodotto(utente),
            'tipi_riordino': get_tipi_riordino(utente),
            'fasce_prezzo': get_fasce_prezzo(utente),
            'conteggi': conta_fase1(utente),
            'message': f'{count} articoli importati da Excel',
        })
    except Exception as e:
        import traceback
        print(f"[api_importa_excel] ERRORE: {e}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
