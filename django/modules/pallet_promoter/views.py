"""
Modulo views per il modulo Pallet-Promoter.

Gestisce la dashboard, le griglie di assegnazione pallet e testate,
il planning hostess e le API HTMX per il salvataggio asincrono dei dati.
Tutte le view ricevono la richiesta HTTP Django e restituiscono un HttpResponse
(pagina HTML o JSON per le API).
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from .models import (
    Periodo, Pallet, Testata, Fornitore, Buyer, Agenzia,
    AssegnazionePallet, AssegnazioneTestata,
    Hostess, PresenzaHostess,
)


def get_current_user(request):
    """Recupera lo username dalla sessione portale."""
    session_user = request.session.get('user', {})
    return session_user.get('username', 'anonymous').lower()


# ============================================
# DASHBOARD
# ============================================

def index(request):
    """
    Dashboard principale del modulo Pallet-Promoter.

    Mostra il riepilogo del periodo corrente, le statistiche aggregate
    (pallet assegnati, testate occupate) e le griglie di dettaglio per
    il periodo attivo e il mese in corso.
    """
    oggi = timezone.now().date()
    mese_corrente = oggi.month
    anno_corrente = oggi.year

    # Periodo corrente: quello il cui intervallo di date contiene la data odierna
    periodo_corrente = Periodo.objects.filter(
        data_inizio__lte=oggi,
        data_fine__gte=oggi
    ).first()

    # Statistiche base: conteggio totale pallet e testate configurati
    totale_pallet = Pallet.objects.count()
    totale_testate = Testata.objects.count()

    # Pallet assegnati nel periodo corrente (con fornitore valorizzato)
    if periodo_corrente:
        pallet_assegnati = AssegnazionePallet.objects.filter(
            periodo=periodo_corrente,
            fornitore_id__isnull=False
        ).count()
    else:
        pallet_assegnati = 0

    # Testate assegnate nel mese corrente (con fornitore valorizzato)
    testate_assegnate = AssegnazioneTestata.objects.filter(
        mese=mese_corrente,
        anno=anno_corrente,
        fornitore_id__isnull=False
    ).count()

    # Dettaglio assegnazioni pallet per il periodo corrente, uno per pallet
    assegnazioni_pallet = []
    if periodo_corrente:
        for pallet in Pallet.objects.all().order_by('codice'):
            assegnazione = AssegnazionePallet.objects.filter(
                periodo=periodo_corrente,
                pallet=pallet
            ).first()
            assegnazioni_pallet.append({
                'pallet': pallet,
                'assegnazione': assegnazione,
                # Se l'assegnazione esiste e ha un fornitore, lo includiamo nel dict
                'fornitore': assegnazione.fornitore if assegnazione else None,
            })

    # Dettaglio assegnazioni testate per il mese corrente, una per testata
    assegnazioni_testate = []
    for testata in Testata.objects.all().order_by('locazione'):
        assegnazione = AssegnazioneTestata.objects.filter(
            mese=mese_corrente,
            anno=anno_corrente,
            testata=testata
        ).first()
        assegnazioni_testate.append({
            'testata': testata,
            'assegnazione': assegnazione,
            'fornitore': assegnazione.fornitore if assegnazione else None,
        })

    context = {
        'periodo_corrente': periodo_corrente,
        'oggi': oggi,
        'mese_corrente': mese_corrente,
        'anno_corrente': anno_corrente,
        'totale_pallet': totale_pallet,
        'totale_testate': totale_testate,
        'pallet_assegnati': pallet_assegnati,
        'testate_assegnate': testate_assegnate,
        'assegnazioni_pallet': assegnazioni_pallet,
        'assegnazioni_testate': assegnazioni_testate,
        'current_user': get_current_user(request),
    }
    return render(request, 'pallet_promoter/index.html', context)


# ============================================
# PALLET
# ============================================

def pallet_list(request):
    """
    Lista dei periodi disponibili per la selezione della griglia pallet.

    Permette di filtrare i periodi per anno tramite query string (?anno=YYYY).
    Passa al template la lista dei periodi filtrati e gli anni disponibili
    per il selettore.
    """
    # Salva l'utente in sessione se passato da Angular via query string
    if request.GET.get('_auth_user'):
        request.session['auth_user'] = request.GET.get('_auth_user').lower()
    anno_corrente = timezone.now().year
    # Usa l'anno specificato in query string, altrimenti l'anno corrente
    anno_selezionato = int(request.GET.get('anno', anno_corrente))
    periodi = Periodo.objects.filter(anno=anno_selezionato).order_by('data_inizio')

    # Anni disponibili per il filtro, in ordine decrescente
    anni = Periodo.objects.values_list('anno', flat=True).distinct().order_by('-anno')

    context = {
        'periodi': periodi,
        'anni': anni,
        'anno_selezionato': anno_selezionato,
        'today': timezone.now().date(),
    }
    return render(request, 'pallet_promoter/pallet_list.html', context)


def pallet_griglia(request, periodo_id):
    """
    Griglia di assegnazione pallet per un periodo specifico.

    Mostra tutti i pallet del buyer selezionato con le relative assegnazioni
    fornitore per il periodo indicato. Supporta la selezione del buyer tramite
    query string (?buyer=ID); se non specificato, tenta il match automatico
    con lo username dell'utente loggato.
    """
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    current_user = get_current_user(request)

    buyer_list = Buyer.objects.exclude(nominativo__isnull=True).exclude(nominativo='').order_by('nominativo')

    # Buyer selezionato (da query string, oppure cerca buyer corrispondente all'utente)
    buyer_id = request.GET.get('buyer')
    buyer_selezionato = None

    if buyer_id:
        buyer_selezionato = Buyer.objects.filter(pk=buyer_id).first()
        pass  # tutti gli utenti hanno accesso a tutti i buyer

    # Se non specificato, cerca buyer con nominativo corrispondente all'utente loggato.
    # Lo username è tipicamente in formato "nome.cognome" o "cognome.nome",
    # quindi viene spezzato e ogni parte viene cercata nel campo nominativo.
    if not buyer_selezionato and current_user:
        parti_username = current_user.lower().replace('.', ' ').split()
        for parte in parti_username:
            if len(parte) > 2:  # ignora parti troppo corte (es. iniziali)
                buyer_match = buyer_list.filter(nominativo__icontains=parte).first()
                if buyer_match:
                    buyer_selezionato = buyer_match
                    break

    # Fallback: se non si trova nessuna corrispondenza, seleziona il primo buyer disponibile
    if not buyer_selezionato:
        buyer_selezionato = buyer_list.first()

    # Mostra il dropdown solo se ci sono più buyer (altrimenti è superfluo)
    mostra_dropdown = buyer_list.count() > 1

    # Costruisce il dizionario pallet→assegnazione per il buyer selezionato
    pallet_per_buyer = {}
    if buyer_selezionato:
        pallet = Pallet.objects.filter(buyer=buyer_selezionato).order_by('codice')
        assegnazioni = {}

        for p in pallet:
            # Recupera l'assegnazione del pallet per questo periodo (può essere None)
            assegn = AssegnazionePallet.objects.filter(
                periodo=periodo, pallet=p
            ).first()
            assegnazioni[p.id] = assegn

        if pallet.exists():
            pallet_per_buyer[buyer_selezionato] = {
                'pallet': pallet,
                'assegnazioni': assegnazioni,
            }

    # Ricostruisce la lista buyer come lista Python per poter aggiungere l'attributo is_selected
    buyer_list = list(Buyer.objects.exclude(nominativo__isnull=True).exclude(nominativo='').order_by('nominativo'))

    # Aggiunge attributo dinamico is_selected per evidenziare il buyer attivo nel dropdown
    for buyer in buyer_list:
        buyer.is_selected = (buyer_selezionato and buyer.id == buyer_selezionato.id)

    context = {
        'periodo': periodo,
        'pallet_per_buyer': pallet_per_buyer,
        'buyer_list': buyer_list,
        'buyer_selezionato': buyer_selezionato,
        'mostra_dropdown': mostra_dropdown,
        'current_user': current_user,
    }
    return render(request, 'pallet_promoter/pallet_griglia.html', context)


# ============================================
# TESTATE
# ============================================

def testate_list(request):
    """
    Pagina di selezione mese/anno per la griglia testate.

    Mostra una griglia cliccabile con i 12 mesi dell'anno corrente;
    l'utente seleziona il mese desiderato per accedere alla griglia
    di assegnazione testate.
    """
    anno_corrente = timezone.now().year
    mese_corrente = timezone.now().month

    context = {
        'anno': anno_corrente,
        'mese': mese_corrente,
        'mesi': range(1, 13),
        # Range di anni mostrati nel selettore: anno precedente, corrente, prossimo
        'anni': range(anno_corrente - 1, anno_corrente + 2),
    }
    return render(request, 'pallet_promoter/testate_list.html', context)


def testate_griglia(request, anno, mese):
    """
    Griglia di assegnazione testate per il mese e anno specificati.

    Per ogni testata crea (o recupera) la relativa AssegnazioneTestata tramite
    get_or_create, in modo da avere sempre un record su cui operare. Calcola
    anche i contatori di testate assegnate, libere e bloccate per le statistiche.
    """
    testate = Testata.objects.all().order_by('id')
    anno_corrente = timezone.now().year

    assegnazioni = {}
    count_assegnate = 0
    count_bloccate = 0

    for t in testate:
        # get_or_create garantisce l'esistenza del record di assegnazione per ogni testata
        assegn, created = AssegnazioneTestata.objects.get_or_create(
            testata=t, anno=anno, mese=mese
        )
        assegnazioni[t.id] = assegn

        # Conta le testate con fornitore valorizzato
        if assegn and assegn.fornitore_id:
            count_assegnate += 1
        # Conta le testate marcate come bloccate (non modificabili)
        if t.bloccata:
            count_bloccate += 1

    # Le testate libere sono quelle né assegnate né bloccate
    count_libere = testate.count() - count_assegnate - count_bloccate

    context = {
        'anno': anno,
        'mese': mese,
        'testate': testate,
        'assegnazioni': assegnazioni,
        # Range di anni per la navigazione nel selettore mese/anno
        'anni': range(anno_corrente - 2, anno_corrente + 2),
        'count_assegnate': count_assegnate,
        'count_libere': count_libere,
        'count_bloccate': count_bloccate,
        'current_user': get_current_user(request),
    }
    return render(request, 'pallet_promoter/testate_griglia.html', context)


# ============================================
# HOSTESS
# ============================================

def hostess_planning(request):
    """
    Planning settimanale hostess — schermata di individuazione hostess per slot.

    Mostra una card per ogni slot hostess del periodo selezionato, con i campi
    per fornitore, hostess, agenzia e orari di ingresso/uscita mattino/pomeriggio.
    Supporta la navigazione giorno per giorno all'interno del periodo.
    Il giorno selezionato si imposta via query string (?giorno=YYYY-MM-DD).
    """
    from datetime import timedelta

    # Trova il periodo corrente o quello selezionato via query string
    oggi = timezone.now().date()
    periodo_id = request.GET.get('periodo')

    if periodo_id:
        periodo = Periodo.objects.filter(pk=periodo_id).first()
    else:
        # Cerca il periodo attivo oggi
        periodo = Periodo.objects.filter(
            data_inizio__lte=oggi,
            data_fine__gte=oggi
        ).first()

    if not periodo:
        # Se non c'è un periodo attivo, prende il prossimo periodo futuro
        periodo = Periodo.objects.filter(data_inizio__gt=oggi).order_by('data_inizio').first()

    if not periodo:
        # Nessun periodo disponibile: mostra pagina di avviso
        return render(request, 'pallet_promoter/hostess_no_periodo.html')

    # Giorno selezionato (default: oggi se nel periodo, altrimenti primo giorno del periodo)
    giorno_str = request.GET.get('giorno')
    if giorno_str:
        try:
            giorno = timezone.datetime.strptime(giorno_str, '%Y-%m-%d').date()
        except:
            giorno = oggi
    else:
        if periodo.data_inizio <= oggi <= periodo.data_fine:
            giorno = oggi
        else:
            giorno = periodo.data_inizio

    # Assicurati che il giorno sia nell'intervallo del periodo
    if giorno < periodo.data_inizio:
        giorno = periodo.data_inizio
    elif giorno > periodo.data_fine:
        giorno = periodo.data_fine

    # Calcola il giorno precedente e successivo per la navigazione (None se ai bordi)
    giorno_prec = giorno - timedelta(days=1) if giorno > periodo.data_inizio else None
    giorno_succ = giorno + timedelta(days=1) if giorno < periodo.data_fine else None

    # Numero di slot hostess attivi: prende il valore dal periodo, max 13
    num_slots = min(periodo.num_hostess or 12, 13)

    # Carica le presenze per il giorno selezionato.
    # Se la presenza non esiste in DB, crea un oggetto non salvato come placeholder.
    presenze = {}
    for slot in range(1, num_slots + 1):
        presenza = PresenzaHostess.objects.filter(giorno=giorno, slot=slot).first()
        if not presenza:
            # Oggetto vuoto (non persistito) per avere sempre un valore nel template
            presenza = PresenzaHostess(giorno=giorno, slot=slot)
        presenze[slot] = presenza

    # Costruisce la lista di tutti i giorni del periodo con il riepilogo presenze
    giorni_periodo = []
    current = periodo.data_inizio
    while current <= periodo.data_fine:
        # Carica tutte le presenze del giorno in una sola query con select_related
        presenze_giorno = PresenzaHostess.objects.filter(giorno=current).select_related('hostess', 'agenzia')
        giorni_periodo.append({
            'data': current,
            'presenze': list(presenze_giorno),
        })
        current += timedelta(days=1)

    # Liste per i dropdown dei form (solo hostess attive)
    hostess_list = Hostess.objects.filter(attiva=True).order_by('nominativo')
    agenzie_list = Agenzia.objects.all().order_by('descrizione')

    context = {
        'periodo': periodo,
        'giorno': giorno,
        'giorno_prec': giorno_prec,
        'giorno_succ': giorno_succ,
        'num_slots': num_slots,
        'slots': range(1, num_slots + 1),
        'presenze': presenze,
        'giorni_periodo': giorni_periodo,
        'hostess_list': hostess_list,
        'agenzie_list': agenzie_list,
        'current_user': get_current_user(request),
    }
    return render(request, 'pallet_promoter/hostess_planning.html', context)


def presenze_list(request):
    """
    Lista delle presenze/timbrature hostess per la data odierna.

    Mostra in sola lettura tutte le presenze registrate nel giorno corrente,
    con orari di ingresso/uscita mattino e pomeriggio.
    """
    oggi = timezone.now().date()

    # Recupera le presenze odierne con i dati correlati in una sola query
    presenze = PresenzaHostess.objects.filter(
        giorno=oggi
    ).select_related('hostess', 'agenzia').order_by('slot')

    context = {
        'presenze': presenze,
        'giorno': oggi,
    }
    return render(request, 'pallet_promoter/presenze_list.html', context)


def scelta_fornitore_hostess(request):
    """
    Schermata Scelta Fornitore per Hostess — griglia settimanale.

    Mostra una tabella con le righe = giorni del periodo e le colonne = slot hostess.
    Ogni cella contiene un campo di ricerca fornitore e un campo note.
    Il salvataggio avviene automaticamente slot per slot via AJAX al blur del campo nota
    o alla selezione del fornitore.
    """
    from datetime import timedelta

    oggi = timezone.now().date()
    periodo_id = request.GET.get('periodo')

    if periodo_id:
        periodo = Periodo.objects.filter(pk=periodo_id).first()
    else:
        # Cerca il periodo attivo oggi
        periodo = Periodo.objects.filter(
            data_inizio__lte=oggi,
            data_fine__gte=oggi
        ).first()

    if not periodo:
        # Se non attivo, prende il prossimo periodo futuro
        periodo = Periodo.objects.filter(data_inizio__gt=oggi).order_by('data_inizio').first()

    if not periodo:
        return render(request, 'pallet_promoter/hostess_no_periodo.html')

    # Numero slot hostess: max 13 per compatibilità con il layout
    num_slots = min(periodo.num_hostess or 12, 13)

    # Costruisce la griglia: lista di giorni, ognuno con un dizionario slot→presenza
    giorni = []
    current = periodo.data_inizio
    while current <= periodo.data_fine:
        presenze_giorno = {}
        for slot in range(1, num_slots + 1):
            presenza = PresenzaHostess.objects.filter(giorno=current, slot=slot).first()
            presenze_giorno[slot] = presenza

        giorni.append({
            'data': current,
            'presenze': presenze_giorno,
        })
        current += timedelta(days=1)

    # Lista periodi per il dropdown di selezione nella barra header (ultimi 50 periodi recenti)
    periodi = Periodo.objects.filter(anno__gte=oggi.year - 1).order_by('-data_inizio')[:50]

    context = {
        'periodo': periodo,
        'periodi': periodi,
        'giorni': giorni,
        'num_slots': num_slots,
        'slots': range(1, num_slots + 1),
        'current_user': get_current_user(request),
    }
    return render(request, 'pallet_promoter/scelta_fornitore_hostess.html', context)


# ============================================
# API HTMX
# ============================================
@require_http_methods(["POST"])
def assegna_pallet(request):
    """
    API HTMX: assegna un pallet a un fornitore per un dato periodo.

    Riceve via POST: pallet_id, periodo_id, fornitore_id (opzionale), dettaglio.
    Usa update_or_create per creare o aggiornare l'assegnazione esistente.
    Ritorna il frammento HTML della cella aggiornata (partial pallet_cell.html).
    """
    pallet_id = request.POST.get('pallet_id')
    periodo_id = request.POST.get('periodo_id')
    fornitore_id = request.POST.get('fornitore_id')
    dettaglio = request.POST.get('dettaglio', '')

    pallet = get_object_or_404(Pallet, pk=pallet_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id)

    # Crea o aggiorna l'assegnazione; fornitore_id None rimuove l'assegnazione
    assegn, created = AssegnazionePallet.objects.update_or_create(
        pallet=pallet,
        periodo=periodo,
        defaults={
            'fornitore_id': int(fornitore_id) if fornitore_id else None,
            'dettaglio': dettaglio,
            'modificato_da': get_current_user(request),
        }
    )

    # Ritorna il fragment HTML aggiornato (usato da HTMX per aggiornare la cella)
    return render(request, 'pallet_promoter/partials/pallet_cell.html', {
        'pallet': pallet,
        'assegnazione': assegn,
        'periodo': periodo,
    })

@require_http_methods(["POST"])
def assegna_testata(request):
    """
    API HTMX: assegna una testata a un fornitore per un dato mese/anno.

    Riceve via POST: testata_id, anno, mese, fornitore_id (opzionale).
    Aggiorna il log dell'assegnazione con l'azione eseguita (aggiunta o rimozione).
    Ritorna il frammento HTML della riga testata aggiornata (partial testata_cell.html).
    """
    testata_id = request.POST.get('testata_id')
    anno = int(request.POST.get('anno'))
    mese = int(request.POST.get('mese'))
    fornitore_id = request.POST.get('fornitore_id')

    testata = get_object_or_404(Testata, pk=testata_id)
    utente = get_current_user(request)

    # Crea o aggiorna l'assegnazione; fornitore_id None libera la testata
    assegn, created = AssegnazioneTestata.objects.update_or_create(
        testata=testata,
        anno=anno,
        mese=mese,
        defaults={
            'fornitore_id': int(fornitore_id) if fornitore_id else None,
            'modificato_da': utente,
        }
    )

    # Aggiorna il log testuale dell'assegnazione con l'azione eseguita
    if fornitore_id:
        forn = assegn.fornitore  # Usa la property per ottenere i dettagli del fornitore
        azione = f"AGGIUNTA TESTATA: {testata.id}-{forn.codice if forn else ''}-{forn.nome if forn else ''}"
    else:
        azione = f"RIMOSSA TESTATA N°: {testata.id}"
    assegn.aggiungi_log(azione, utente)
    assegn.save()

    return render(request, 'pallet_promoter/partials/testata_cell.html', {
        'testata': testata,
        'assegnazione': assegn,
        'anno': anno,
        'mese': mese,
    })


@require_http_methods(["POST"])
def salva_presenza_hostess(request):
    """
    API: salva la presenza di una singola hostess per giorno e slot.

    Riceve via POST i dati di un singolo slot (fornitore, hostess, agenzia,
    orari mattino/pomeriggio, note). Crea o aggiorna il record PresenzaHostess.
    Risponde con JSON {success: True, id: <id>}.
    """
    import json
    from datetime import datetime

    giorno_str = request.POST.get('giorno')
    slot = int(request.POST.get('slot'))

    giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()

    # Recupera o crea la presenza per il giorno/slot specificati
    presenza, created = PresenzaHostess.objects.get_or_create(
        giorno=giorno,
        slot=slot,
        defaults={'tipo': 'STD'}
    )

    # Aggiorna il fornitore (None se non selezionato)
    fornitore_id = request.POST.get('fornitore_id')
    presenza.fornitore_id = int(fornitore_id) if fornitore_id else None
    presenza.nota_fornitore = request.POST.get('nota_fornitore', '')

    # Aggiorna la hostess (None se non selezionata)
    hostess_id = request.POST.get('hostess_id')
    presenza.hostess = Hostess.objects.filter(pk=hostess_id).first() if hostess_id else None

    # Aggiorna l'agenzia (None se non selezionata)
    agenzia_id = request.POST.get('agenzia_id')
    presenza.agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None

    # Funzione helper interna per il parsing degli orari HH:MM
    def parse_time(val):
        if not val:
            return None
        try:
            return datetime.strptime(val, '%H:%M').time()
        except:
            return None

    presenza.ingresso_mattino = parse_time(request.POST.get('ingresso_mattino'))
    presenza.uscita_mattino = parse_time(request.POST.get('uscita_mattino'))
    presenza.ingresso_pomeriggio = parse_time(request.POST.get('ingresso_pomeriggio'))
    presenza.uscita_pomeriggio = parse_time(request.POST.get('uscita_pomeriggio'))

    presenza.nota = request.POST.get('varie', '')

    presenza.save()

    return JsonResponse({'success': True, 'id': presenza.id})

@require_http_methods(["POST"])
def salva_tutte_presenze(request):
    """
    API: salva tutte le presenze di un giorno in una sola chiamata (bulk save).

    Riceve un JSON nel body con: giorno (stringa YYYY-MM-DD) e presenze (lista
    di oggetti con i dati di ogni slot). Itera su ogni slot e salva il record.
    Risponde con JSON {success: True, saved: <num_salvati>}.
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

        # Crea o recupera il record per il giorno/slot
        presenza, created = PresenzaHostess.objects.get_or_create(
            giorno=giorno,
            slot=slot,
            defaults={'tipo': 'STD'}
        )

        # Aggiorna tutti i campi del record
        fornitore_id = p.get('fornitore_id')
        presenza.fornitore_id = int(fornitore_id) if fornitore_id else None
        presenza.nota_fornitore = p.get('nota_fornitore', '') or ''

        hostess_id = p.get('hostess_id')
        presenza.hostess = Hostess.objects.filter(pk=hostess_id).first() if hostess_id else None

        agenzia_id = p.get('agenzia_id')
        presenza.agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None

        # Funzione helper interna per il parsing degli orari HH:MM
        def parse_time(val):
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


def cerca_fornitore(request):
    """
    API per l'autocomplete dei fornitori (usata da HTMX e JavaScript).

    Riceve il parametro ?q= con la stringa di ricerca (min 2 caratteri).
    Filtra i fornitori per nome o codice (case-insensitive) e ritorna
    il partial HTML con la lista dei risultati (max 20 elementi).
    """
    q = request.GET.get('q', '')

    # Non avviare la ricerca per query troppo corte (evita risultati troppo ampi)
    if len(q) < 2:
        return render(request, 'pallet_promoter/partials/fornitore_results.html', {'results': []})

    # Ricerca su nome O codice fornitore, limite a 20 risultati
    fornitori = Fornitore.objects.filter(
        Q(nome__icontains=q) | Q(codice__icontains=q)
    )[:20]

    results = [
        {'id': f.codice, 'text': f"{f.codice} - {f.nome}"}
        for f in fornitori
    ]

    return render(request, 'pallet_promoter/partials/fornitore_results.html', {'results': results})

@require_http_methods(["POST"])
def salva_fornitore_slot(request):
    """
    API: salva il fornitore per un singolo slot/giorno nella griglia scelta fornitore.

    Usata dalla griglia scelta_fornitore_hostess per il salvataggio automatico
    slot per slot (chiamata al blur del campo nota o alla selezione fornitore).
    Riceve via POST: giorno, slot, fornitore_id (opzionale), nota.
    """
    from datetime import datetime

    giorno_str = request.POST.get('giorno')
    slot = int(request.POST.get('slot'))
    fornitore_id = request.POST.get('fornitore_id')
    nota = request.POST.get('nota', '')

    giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()

    # Crea o recupera il record di presenza per il giorno/slot
    presenza, created = PresenzaHostess.objects.get_or_create(
        giorno=giorno,
        slot=slot,
        defaults={'tipo': 'STD'}
    )

    # Aggiorna solo il fornitore e la nota (gli altri campi rimangono invariati)
    presenza.fornitore_id = int(fornitore_id) if fornitore_id else None
    presenza.nota_fornitore = nota
    presenza.save()

    return JsonResponse({'success': True})