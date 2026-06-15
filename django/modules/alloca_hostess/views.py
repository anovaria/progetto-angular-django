from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q

from modules.pallet_promoter.models import (
    Agenzia, Buyer, Hostess, Fornitore, Periodo, PresenzaHostess, SlotPolmone, IngressoUscitaPolmone
)

"""
Modulo views per il modulo Alloca Hostess.

Gestisce le operazioni di allocazione, coordinamento e registrazione
delle presenze e degli orari delle hostess nei vari slot di lavoro.
Include anche la gestione delle attività non previste (es. rilevamento prezzi)
tramite il registro del polmone (SlotPolmone / IngressoUscitaPolmone).
"""


def get_current_user(request):
    """Recupera lo username dalla sessione portale."""
    session_user = request.session.get('user', {})
    return session_user.get('username', 'anonymous').lower()


def index(request):
    """Dashboard Alloca Hostess."""
    oggi = timezone.now().date()

    # Cerca il periodo promozionale attivo alla data odierna
    periodo_corrente = Periodo.objects.filter(
        data_inizio__lte=oggi,
        data_fine__gte=oggi
    ).first()

    # Statistiche generali da mostrare nelle card
    hostess_attive = Hostess.objects.filter(attiva=True).count()
    agenzie_count = Agenzia.objects.count()

    # Numero slot dal periodo (default 12, massimo consentito 13)
    num_slots = 12
    if periodo_corrente and periodo_corrente.num_hostess:
        num_slots = min(periodo_corrente.num_hostess, 13)

    # Costruisce la lista di tutti gli slot per il giorno odierno,
    # con o senza hostess assegnata, per visualizzarla nella dashboard
    presenze_oggi_list = []
    presenze_con_hostess = 0

    for slot_num in range(1, num_slots + 1):
        # Recupera la presenza esistente per questo slot, se presente
        presenza = PresenzaHostess.objects.filter(
            giorno=oggi,
            slot=slot_num
        ).select_related('hostess', 'agenzia', 'buyer').first()

        # Conta solo gli slot con una hostess effettivamente assegnata
        if presenza and presenza.hostess:
            presenze_con_hostess += 1

        presenze_oggi_list.append({
            'slot': slot_num,
            'presenza': presenza,
        })

    context = {
        'periodo_corrente': periodo_corrente,
        'hostess_attive': hostess_attive,
        'agenzie_count': agenzie_count,
        'presenze_oggi': presenze_con_hostess,
        'presenze_oggi_list': presenze_oggi_list,
        'num_slots': num_slots,
        'oggi': oggi,
        'current_user': get_current_user(request),
    }
    return render(request, 'alloca_hostess/index.html', context)

def hostess_list(request):
    """Elenco Hostess."""
    hostess = Hostess.objects.all().order_by('nominativo')

    # Il parametro GET 'attive' filtra solo le hostess attive (default: sì)
    solo_attive = request.GET.get('attive', '1') == '1'
    if solo_attive:
        hostess = hostess.filter(attiva=True)

    context = {
        'hostess_list': hostess,
        'solo_attive': solo_attive,
        'current_user': get_current_user(request),
    }
    return render(request, 'alloca_hostess/hostess_list.html', context)


def agenzie_list(request):
    """Elenco Agenzie."""
    agenzie = Agenzia.objects.all().order_by('descrizione')

    context = {
        'agenzie_list': agenzie,
        'current_user': get_current_user(request),
    }
    return render(request, 'alloca_hostess/agenzie_list.html', context)


def individuazione(request):
    """
    Vista principale per l'individuazione e il coordinamento delle hostess.

    Gestisce la visualizzazione e modifica degli slot giornalieri all'interno
    di un periodo selezionato. Supporta la navigazione tra periodi e giorni,
    il riepilogo storico del periodo e il modal per la copia degli slot.
    """
    from datetime import timedelta
    import json

    oggi = timezone.now().date()
    periodo_id = request.GET.get('periodo')

    # Carica tutti i periodi per il selettore a tendina (ordinati dal più recente)
    tutti_periodi = Periodo.objects.all().order_by('-data_inizio')

    # Determina il periodo da visualizzare: quello selezionato, quello corrente,
    # il prossimo futuro, oppure l'ultimo disponibile
    if periodo_id:
        periodo = Periodo.objects.filter(pk=periodo_id).first()
    else:
        periodo = Periodo.objects.filter(
            data_inizio__lte=oggi,
            data_fine__gte=oggi
        ).first()

    if not periodo:
        periodo = Periodo.objects.filter(data_inizio__gt=oggi).order_by('data_inizio').first()

    if not periodo:
        periodo = Periodo.objects.order_by('-data_fine').first()

    # Se non esiste nessun periodo nel sistema, mostra pagina di errore dedicata
    if not periodo:
        return render(request, 'alloca_hostess/no_periodo.html')

    # Navigazione periodi: trova il precedente e il successivo per le frecce di navigazione
    periodo_prec = Periodo.objects.filter(data_fine__lt=periodo.data_inizio).order_by('-data_fine').first()
    periodo_succ = Periodo.objects.filter(data_inizio__gt=periodo.data_fine).order_by('data_inizio').first()

    # Determina il giorno selezionato dal parametro GET, oppure usa oggi se nel periodo
    giorno_str = request.GET.get('giorno')
    if giorno_str:
        try:
            giorno = timezone.datetime.strptime(giorno_str, '%Y-%m-%d').date()
        except:
            giorno = oggi
    else:
        # Se oggi è nel periodo, mostra oggi; altrimenti vai al primo giorno del periodo
        if periodo.data_inizio <= oggi <= periodo.data_fine:
            giorno = oggi
        else:
            giorno = periodo.data_inizio

    # Costringe il giorno selezionato entro i limiti del periodo
    if giorno < periodo.data_inizio:
        giorno = periodo.data_inizio
    elif giorno > periodo.data_fine:
        giorno = periodo.data_fine

    # Calcola i giorni adiacenti per i pulsanti di navigazione (None se al limite)
    giorno_prec = giorno - timedelta(days=1) if giorno > periodo.data_inizio else None
    giorno_succ = giorno + timedelta(days=1) if giorno < periodo.data_fine else None

    # Numero massimo di slot attivi nel periodo (cap a 13)
    num_slots = min(periodo.num_hostess or 12, 13)

    # Carica le presenze del giorno: per ogni slot crea un oggetto (anche vuoto, non salvato)
    presenze = {}
    for slot in range(1, num_slots + 1):
        presenza = PresenzaHostess.objects.filter(giorno=giorno, slot=slot).select_related('hostess', 'agenzia', 'buyer').first()
        if not presenza:
            # Crea un'istanza non salvata per slot ancora privi di assegnazione
            presenza = PresenzaHostess(giorno=giorno, slot=slot)
        presenze[slot] = presenza

    # Costruisce lo storico del periodo: lista di giorni con le relative presenze
    giorni_periodo = []
    current = periodo.data_inizio
    while current <= periodo.data_fine:
        presenze_giorno = PresenzaHostess.objects.filter(giorno=current).select_related('hostess', 'agenzia', 'buyer')
        giorni_periodo.append({
            'data': current,
            'presenze': list(presenze_giorno),
        })
        current += timedelta(days=1)

    # Costruisce struttura periodi/giorni per il modal di copia slot
    periodi_giorni = []
    for p in Periodo.objects.all().order_by('data_inizio'):
        giorni_p = []
        d = p.data_inizio
        while d <= p.data_fine:
            giorni_p.append(d)
            d += timedelta(days=1)
        periodi_giorni.append({
            'id': p.id,
            'label': f"{p.data_inizio.strftime('%d/%m/%Y')} → {p.data_fine.strftime('%d/%m/%Y')}",
            'giorni': giorni_p,
        })

    # Dizionario JSON con tutti i giorni che hanno almeno una hostess assegnata,
    # usato lato client per evidenziare i giorni con dati nel modal di copia slot.
    # Usa una singola query su tutti i periodi per efficienza.
    tutti_giorni_json = {}
    tutte_presenze = PresenzaHostess.objects.filter(
        hostess__isnull=False
    ).values('giorno', 'slot')
    for p in tutte_presenze:
        key = p['giorno'].strftime('%Y-%m-%d')
        if key not in tutti_giorni_json:
            tutti_giorni_json[key] = {'presenze': {}}
        # La chiave dello slot è stringa per compatibilità con JS
        tutti_giorni_json[key]['presenze'][str(p['slot'])] = True

    # Liste per i dropdown di selezione nel form slot
    hostess_list = Hostess.objects.filter(attiva=True).order_by('nominativo')
    agenzie_list = Agenzia.objects.all().order_by('descrizione')

    context = {
        'periodo': periodo,
        'tutti_periodi': tutti_periodi,
        'periodo_prec': periodo_prec,
        'periodo_succ': periodo_succ,
        'giorno': giorno,
        'giorno_prec': giorno_prec,
        'giorno_succ': giorno_succ,
        'num_slots': num_slots,
        'slots': range(1, num_slots + 1),
        'presenze': presenze,
        'giorni_periodo': giorni_periodo,
        'hostess_list': hostess_list,
        'agenzie_list': agenzie_list,
        'buyer_list': Buyer.objects.all().order_by('nominativo'),
        'current_user': get_current_user(request),
        'oggi': oggi,
        'periodi_giorni': periodi_giorni,
        'giorni_periodo_json': json.dumps(tutti_giorni_json),
    }
    return render(request, 'alloca_hostess/individuazione.html', context)

@require_http_methods(["GET"])
def cerca_fornitore(request):
    """
    API per la ricerca AJAX dei fornitori tramite autocompletamento.

    Richiede almeno 2 caratteri nella query, restituisce un partial HTML
    con al massimo 15 risultati corrispondenti.
    """
    q = request.GET.get('q', '').strip()
    # Restituisce lista vuota se la ricerca è troppo corta
    if len(q) < 2:
        return render(request, 'alloca_hostess/partials/fornitore_results.html', {'fornitori': []})

    fornitori = Fornitore.objects.filter(nome__icontains=q)[:15]
    return render(request, 'alloca_hostess/partials/fornitore_results.html', {'fornitori': fornitori})


@require_http_methods(["POST"])
def salva_presenze(request):
    """
    Salva tutte le presenze di un intero giorno in un'unica chiamata.

    Riceve un payload JSON con il giorno e la lista di presenze per slot.
    Per ogni slot esegue get_or_create e aggiorna tutti i campi (fornitore,
    hostess, agenzia, buyer, orari mattina/pomeriggio, note).
    """
    import json
    from datetime import datetime

    data = json.loads(request.body)
    giorno_str = data.get('giorno')
    presenze_data = data.get('presenze', [])

    giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()

    saved = 0
    for p in presenze_data:
        slot = int(p.get('slot'))

        # Crea il record se non esiste, oppure recupera quello esistente
        presenza, created = PresenzaHostess.objects.get_or_create(
            giorno=giorno,
            slot=slot,
            defaults={'tipo': 'STD'}
        )

        # Aggiorna i campi FK: usa None se l'ID non è fornito
        fornitore_id = p.get('fornitore_id')
        presenza.fornitore_id = p.get('fornitore_id') or None
        presenza.nota_fornitore = p.get('nota_fornitore', '') or ''

        hostess_id = p.get('hostess_id')
        presenza.hostess = Hostess.objects.filter(pk=hostess_id).first() if hostess_id else None

        agenzia_id = p.get('agenzia_id')
        presenza.agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None

        buyer_id = p.get('buyer_id')
        presenza.buyer = Buyer.objects.filter(pk=buyer_id).first() if buyer_id else None

        def parse_time(val):
            """Converte una stringa 'HH:MM' in oggetto time; ritorna None se vuota o non valida."""
            if not val:
                return None
            try:
                return datetime.strptime(val, '%H:%M').time()
            except:
                return None

        presenza.ingresso_mattino = parse_time(p.get('ingresso_mattino'))
        presenza.uscita_mattino = parse_time(p.get('uscita_mattino'))
        presenza.ingresso_pomeriggio = parse_time(p.get('ingresso_pomeriggio'))
        presenza.uscita_pomeriggio = parse_time(p.get('uscita_pomeriggio'))

        presenza.nota = p.get('varie', '') or ''

        presenza.save()
        saved += 1

    return JsonResponse({'success': True, 'saved': saved})


# ============================================
# REGISTRAZIONE ORARI HOSTESS (Punto Info)
# ============================================

def orari_hostess(request):
    """
    Vista per la registrazione degli orari giornalieri delle hostess.

    Pensata per l'uso da Punto Info. Mostra tutti gli slot (1-12) per
    la data selezionata con i relativi campi orario. I dati di giorni
    passati o futuri sono visualizzati in sola lettura.
    """
    oggi = timezone.now().date()

    # Legge la data dal parametro GET, con fallback alla data odierna
    data_str = request.GET.get('data')
    if data_str:
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data = oggi
    else:
        data = oggi

    # Date per le frecce di navigazione giorno precedente/successivo
    data_prec = data - timedelta(days=1)
    data_succ = data + timedelta(days=1)

    # Se la data non è oggi, la pagina diventa di sola lettura (nessuna modifica)
    is_readonly = data != oggi

    # Costruisce la lista degli slot con le relative presenze (o istanze vuote)
    presenze_hostess = []
    for slot_num in range(1, 13):  # 12 slot fissi per questa vista
        presenza = PresenzaHostess.objects.filter(
            giorno=data,
            slot=slot_num
        ).select_related('hostess', 'agenzia').first()

        if not presenza:
            # Crea oggetto vuoto (non salvato) per mostrare lo slot disponibile
            presenza = PresenzaHostess(giorno=data, slot=slot_num)

        presenze_hostess.append({
            'slot': slot_num,
            'presenza': presenza,
        })

    context = {
        'data': data,
        'data_prec': data_prec,
        'data_succ': data_succ,
        'is_readonly': is_readonly,
        'presenze_hostess': presenze_hostess,
        'current_user': get_current_user(request),
    }
    return render(request, 'alloca_hostess/orari_hostess.html', context)


@require_http_methods(["POST"])
def salva_orario_hostess(request):
    """
    Salva gli orari di un singolo slot per un giorno specifico.

    Riceve i dati via POST (form standard), esegue get_or_create
    sulla presenza e aggiorna i quattro campi orario più la nota.
    """
    giorno_str = request.POST.get('giorno')
    slot = request.POST.get('slot')

    try:
        giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()
    except:
        return JsonResponse({'success': False, 'error': 'Data non valida'})

    # Prendi la presenza esistente o creane una nuova per questo slot/giorno
    presenza, created = PresenzaHostess.objects.get_or_create(
        giorno=giorno,
        slot=slot
    )

    def parse_time(val):
        """Converte una stringa 'HH:MM' in oggetto time; ritorna None se vuota o non valida."""
        if not val:
            return None
        try:
            return datetime.strptime(val, '%H:%M').time()
        except:
            return None

    # Aggiorna i quattro campi orario
    presenza.ingresso_mattino = parse_time(request.POST.get('ingresso_mattino'))
    presenza.uscita_mattino = parse_time(request.POST.get('uscita_mattino'))
    presenza.ingresso_pomeriggio = parse_time(request.POST.get('ingresso_pomeriggio'))
    presenza.uscita_pomeriggio = parse_time(request.POST.get('uscita_pomeriggio'))

    # Salva la nota testuale (None se vuota, per non salvare stringhe vuote)
    nota = request.POST.get('nota', '').strip()
    presenza.nota = nota if nota else None

    presenza.save()

    return JsonResponse({'success': True})
# ============================================
# ATTIVITÀ NON PREVISTE (Rilevamento Prezzi)
# ============================================

def attivita_non_previste(request):
    """
    Vista per la gestione delle attività non previste dal Punto Info.

    Mostra una tabella con tutti i nominativi del polmone (SlotPolmone)
    e i loro eventuali orari di ingresso/uscita per la data selezionata.
    Permette la registrazione rapida degli orari con auto-salvataggio.
    """
    from datetime import timedelta

    oggi = timezone.now().date()

    # Legge la data dal parametro GET, con fallback a oggi
    data_str = request.GET.get('data')
    if data_str:
        try:
            data_sel = timezone.datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            data_sel = oggi
    else:
        data_sel = oggi

    # Date per navigazione giorno precedente/successivo
    data_prec = data_sel - timedelta(days=1)
    data_succ = data_sel + timedelta(days=1)

    # Carica tutti i nominativi attivi (da_eliminare=False) per popolare la tabella
    nominativi_list = SlotPolmone.objects.filter(da_eliminare=False).order_by('nominativo')

    # Recupera le attività del giorno selezionato che hanno almeno un orario compilato
    attivita_giorno = IngressoUscitaPolmone.objects.filter(
        data=data_sel
    ).filter(
        Q(ingresso_1__isnull=False) | Q(uscita_1__isnull=False) |
        Q(ingresso_2__isnull=False) | Q(uscita_2__isnull=False) |
        Q(ingresso_extra_1__isnull=False) | Q(uscita_extra_1__isnull=False)
    ).select_related('slot_polmone')

    # Dizionario per accesso rapido lato template: slot_polmone_id -> attività del giorno
    attivita_dict = {att.slot_polmone_id: att for att in attivita_giorno}

    context = {
        'oggi': oggi,
        'data_sel': data_sel,
        'data_prec': data_prec,
        'data_succ': data_succ,
        'nominativi_list': nominativi_list,
        'attivita_dict': attivita_dict,
        'current_user': get_current_user(request),
    }
    return render(request, 'alloca_hostess/attivita_non_previste.html', context)


@require_http_methods(["GET"])
def cerca_nominativo_polmone(request):
    """
    API per la ricerca AJAX dei nominativi del polmone tramite autocompletamento.

    Richiede almeno 2 caratteri nella query, restituisce JSON con id,
    nominativo e note per ciascun risultato (max 15).
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    nominativi = SlotPolmone.objects.filter(
        nominativo__icontains=q,
        da_eliminare=False
    ).order_by('nominativo')[:15]

    results = [{'id': n.id, 'nominativo': n.nominativo, 'note': n.note or ''} for n in nominativi]
    return JsonResponse({'results': results})


@require_http_methods(["POST"])
def aggiungi_nominativo_polmone(request):
    """
    Aggiunge un nuovo nominativo all'anagrafica delle attività non previste.

    Poiché la tabella è unmanaged e non ha IDENTITY, il nuovo ID viene
    calcolato manualmente con una query SQL (MAX(id) + 1).
    """
    import json
    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    nominativo = (data.get('nominativo') or '').strip()
    note = (data.get('note') or '').strip()

    if not nominativo:
        return JsonResponse({'success': False, 'error': 'Nominativo obbligatorio'})

    # Calcola il prossimo ID manualmente perché la tabella non usa IDENTITY di SQL Server
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT ISNULL(MAX(id), 0) + 1 FROM [shared].[slot_polmone]")
        next_id = cursor.fetchone()[0]

    slot = SlotPolmone.objects.create(
        id=next_id,
        nominativo=nominativo,
        note=note or None,
        da_eliminare=False,
    )
    return JsonResponse({'success': True, 'id': slot.id, 'nominativo': slot.nominativo, 'note': slot.note or ''})


@require_http_methods(["POST"])
def salva_attivita_non_prevista(request):
    """
    Salva o aggiorna un'attività non prevista per un nominativo e una data.

    Se viene fornito un ID esistente, aggiorna il record.
    Se non viene fornito ID ma esiste già un record per slot+data, lo aggiorna.
    Altrimenti crea un nuovo record.
    """
    import json

    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    attivita_id = data.get('id')
    slot_polmone_id = data.get('slot_polmone_id')
    data_str = data.get('data')

    if not slot_polmone_id:
        return JsonResponse({'success': False, 'error': 'Nominativo obbligatorio'})

    if not data_str:
        return JsonResponse({'success': False, 'error': 'Data obbligatoria'})

    try:
        data_attivita = datetime.strptime(data_str, '%Y-%m-%d').date()
    except:
        return JsonResponse({'success': False, 'error': 'Data non valida'})

    # Verifica che il nominativo del polmone esista nel database
    slot_polmone = SlotPolmone.objects.filter(pk=slot_polmone_id).first()
    if not slot_polmone:
        return JsonResponse({'success': False, 'error': 'Nominativo non trovato'})

    def parse_time(val):
        """Converte una stringa 'HH:MM' in oggetto time; ritorna None se vuota o non valida."""
        if not val:
            return None
        try:
            return datetime.strptime(val, '%H:%M').time()
        except:
            return None

    if attivita_id:
        # Modifica un record esistente tramite ID esplicito
        attivita = IngressoUscitaPolmone.objects.filter(pk=attivita_id).first()
        if not attivita:
            return JsonResponse({'success': False, 'error': 'Attività non trovata'})
    else:
        # Nessun ID: cerca se esiste già per questo slot+data, oppure crea nuovo
        attivita = IngressoUscitaPolmone.objects.filter(
            slot_polmone_id=slot_polmone_id,
            data=data_attivita
        ).first()

        if not attivita:
            attivita = IngressoUscitaPolmone()
            attivita.slot_polmone_id = slot_polmone_id
            attivita.data = data_attivita

    # Aggiorna tutti gli orari di ingresso/uscita (inclusi quelli extra)
    attivita.ingresso_1 = parse_time(data.get('ingresso_1'))
    attivita.uscita_1 = parse_time(data.get('uscita_1'))
    attivita.ingresso_2 = parse_time(data.get('ingresso_2'))
    attivita.uscita_2 = parse_time(data.get('uscita_2'))
    attivita.ingresso_extra_1 = parse_time(data.get('ingresso_extra_1'))
    attivita.uscita_extra_1 = parse_time(data.get('uscita_extra_1'))
    attivita.ingresso_extra_2 = parse_time(data.get('ingresso_extra_2'))
    attivita.uscita_extra_2 = parse_time(data.get('uscita_extra_2'))
    # Il campo 'forzato' accetta vari formati truthy provenienti da JS/form
    attivita.forzato = data.get('forzato') in ['true', 'True', True, '1', 1]

    attivita.save()

    return JsonResponse({
        'success': True,
        'id': attivita.id,
        'message': 'Salvato con successo'
    })


@require_http_methods(["POST"])
def elimina_attivita_non_prevista(request):
    """Elimina un'attività non prevista tramite il suo ID."""
    import json

    try:
        data = json.loads(request.body)
    except:
        data = request.POST.dict()

    attivita_id = data.get('id')

    if not attivita_id:
        return JsonResponse({'success': False, 'error': 'ID mancante'})

    attivita = IngressoUscitaPolmone.objects.filter(pk=attivita_id).first()
    if not attivita:
        return JsonResponse({'success': False, 'error': 'Attività non trovata'})

    attivita.delete()

    return JsonResponse({'success': True, 'message': 'Eliminato con successo'})


@require_http_methods(["POST"])
def copia_slot(request):
    """
    Copia i dati di uno slot su una lista di giorni (anche di periodi diversi).

    Riceve un payload JSON con la lista dei giorni di destinazione e i dati
    dello slot sorgente (fornitore, hostess, agenzia, note). Gli orari non
    vengono copiati per evitare sovrascritture involontarie.
    """
    import json
    data = json.loads(request.body)
    giorni = data.get('giorni', [])
    presenza_data = data.get('presenza', {})

    if not giorni:
        return JsonResponse({'success': False, 'error': 'Nessun giorno selezionato'})

    slot = int(presenza_data.get('slot'))
    hostess_id = presenza_data.get('hostess_id')
    agenzia_id = presenza_data.get('agenzia_id')
    # Risolve gli FK una sola volta prima del ciclo per efficienza
    hostess = Hostess.objects.filter(pk=hostess_id).first() if hostess_id else None
    agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None

    saved = 0
    for giorno_str in giorni:
        try:
            giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()
        except ValueError:
            continue  # Salta date malformate senza interrompere il ciclo
        presenza, _ = PresenzaHostess.objects.get_or_create(
            giorno=giorno, slot=slot, defaults={'tipo': 'STD'}
        )
        presenza.fornitore_id = presenza_data.get('fornitore_id') or None
        presenza.nota_fornitore = presenza_data.get('nota_fornitore', '') or ''
        presenza.hostess = hostess
        presenza.agenzia = agenzia
        presenza.nota = presenza_data.get('varie', '') or ''
        presenza.save()
        saved += 1

    return JsonResponse({'success': True, 'saved': saved})


@require_http_methods(["POST"])
def salva_orario_attivita(request):
    """
    Salva gli orari di un'attività non prevista esistente (da tabella inline).

    Aggiorna i campi ingresso/uscita 1, 2 ed extra_1 di un record
    IngressoUscitaPolmone identificato dall'ID passato in POST.
    """
    attivita_id = request.POST.get('id')

    if not attivita_id:
        return JsonResponse({'success': False, 'error': 'ID mancante'})

    attivita = IngressoUscitaPolmone.objects.filter(pk=attivita_id).first()
    if not attivita:
        return JsonResponse({'success': False, 'error': 'Attività non trovata'})

    def parse_time(val):
        """Converte una stringa 'HH:MM' in oggetto time; ritorna None se vuota o non valida."""
        if not val:
            return None
        try:
            return datetime.strptime(val, '%H:%M').time()
        except:
            return None

    # Aggiorna i campi orario disponibili in questa vista semplificata
    attivita.ingresso_1 = parse_time(request.POST.get('ingresso_1'))
    attivita.uscita_1 = parse_time(request.POST.get('uscita_1'))
    attivita.ingresso_2 = parse_time(request.POST.get('ingresso_2'))
    attivita.uscita_2 = parse_time(request.POST.get('uscita_2'))
    attivita.ingresso_extra_1 = parse_time(request.POST.get('ingresso_extra_1'))
    attivita.uscita_extra_1 = parse_time(request.POST.get('uscita_extra_1'))

    attivita.save()

    return JsonResponse({'success': True})
