from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.db import models

from .models import (
    Utente, Merchandiser, Slot, SlotFornitore, SlotIngressoUscita
)
from modules.pallet_promoter.models import Agenzia, Fornitore, Buyer, Hostess, PresenzaHostess

"""
Modulo views per l'applicazione Merchandiser.

Gestisce tutte le viste relative a:
- Dashboard con riepilogo giornaliero degli slot e timbrature
- Anagrafica merchandiser (CRUD completo)
- Anagrafica hostess (CRUD completo)
- Gestione agenzie (CRUD completo)
- Gestione slot (periodi di lavoro assegnati ai merchandiser)
- Registrazione orari di ingresso/uscita per gli slot
- API interne per salvataggio dati via AJAX

L'autenticazione avviene tramite header LDAP HTTP_X_REMOTE_USER.
Le API di modifica usano @csrf_exempt in combinazione con
autenticazione lato proxy, quindi non richiedono token CSRF nel POST.
"""


def get_current_user(request):
    """Recupera lo username dalla sessione portale."""
    session_user = request.session.get('user', {})
    return session_user.get('username', 'anonymous').lower()


# ============================================
# DASHBOARD
# ============================================

def index(request):
    """Dashboard principale Merchandiser."""
    oggi = timezone.now().date()

    # Statistiche
    merchandiser_attivi = Merchandiser.objects.filter(attivo=True).count()
    slot_attivi = Slot.objects.filter(
        attivo=True,
        data_inizio__lte=oggi,
        data_fine__gte=oggi
    ).count()
    timbrature_oggi = SlotIngressoUscita.objects.filter(data=oggi).count()

    # Tutti gli slot attivi oggi
    slot_oggi = Slot.objects.filter(
        attivo=True,
        data_inizio__lte=oggi,
        data_fine__gte=oggi
    ).select_related('merchandiser', 'utente').order_by('merchandiser__cognome', 'merchandiser__nome')

    # Dizionario slot_id -> timbratura per evidenziare chi ha timbrato
    # Usato nel template per mostrare badge verde/giallo per ogni riga slot
    timbrature_dict = {
        t.slot_id: t for t in SlotIngressoUscita.objects.filter(data=oggi)
    }

    context = {
        'merchandiser_attivi': merchandiser_attivi,
        'slot_attivi': slot_attivi,
        'timbrature_oggi': timbrature_oggi,
        'slot_oggi': slot_oggi,
        'timbrature_dict': timbrature_dict,
        'oggi': oggi,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/index.html', context)


# ============================================
# MERCHANDISER (Anagrafica)
# ============================================

def merchandiser_list(request):
    """Lista merchandiser con filtro opzionale sui soli attivi."""
    # Il parametro GET 'attivi' determina se mostrare solo i merchandiser attivi (default: sì)
    solo_attivi = request.GET.get('attivi', '1') == '1'

    merchandiser = Merchandiser.objects.all().order_by('cognome', 'nome')
    if solo_attivi:
        merchandiser = merchandiser.filter(attivo=True)

    context = {
        'merchandiser_list': merchandiser,
        'solo_attivi': solo_attivi,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/merchandiser_list.html', context)


# ============================================
# UTENTI (Referenti)
# ============================================

def utenti_list(request):
    """Lista utenti/referenti con filtro opzionale sui soli attivi."""
    solo_attivi = request.GET.get('attivi', '1') == '1'

    utenti = Utente.objects.all().order_by('cognome', 'nome')
    if solo_attivi:
        utenti = utenti.filter(attivo=True)

    context = {
        'utenti_list': utenti,
        'solo_attivi': solo_attivi,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/utenti_list.html', context)


# ============================================
# AGENZIE
# ============================================

def agenzie_list(request):
    """Lista agenzie (vista sola lettura, senza azioni CRUD)."""
    agenzie = Agenzia.objects.all().order_by('descrizione')

    context = {
        'agenzie_list': agenzie,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/agenzie_list.html', context)


# ============================================
# SLOT (Form principale)
# ============================================

def slot_list(request):
    """Lista slot con filtri per merchandiser, utente e stato attivo/disattivato."""
    oggi = timezone.now().date()

    # Filtri passati come query string
    merchandiser_id = request.GET.get('merchandiser')
    utente_id = request.GET.get('utente')
    solo_attivi = request.GET.get('attivi', '1') == '1'
    cerca = request.GET.get('cerca', '').strip()

    slots = Slot.objects.all().select_related('merchandiser', 'utente')

    if merchandiser_id:
        slots = slots.filter(merchandiser_id=merchandiser_id)
    if utente_id:
        slots = slots.filter(utente_id=utente_id)
    if cerca:
        slots = slots.filter(
            Q(merchandiser__cognome__icontains=cerca) |
            Q(merchandiser__nome__icontains=cerca)
        )
    if solo_attivi:
        # Filtra solo slot che hanno già avuto inizio (data_inizio <= oggi)
        # e non sono ancora terminati (data_fine >= oggi)
        slots = slots.filter(
            attivo=True,
            data_inizio__lte=oggi,   # Già iniziato
            data_fine__gte=oggi      # Non ancora finito
        )

    slots = slots.order_by('merchandiser__cognome', 'merchandiser__nome', '-data_inizio')

    # Applica il limite di 100 solo se non è attivo alcun filtro di ricerca
    if not cerca and not merchandiser_id:
        slots = slots[:100]

    # Liste per i menu a tendina dei filtri
    merchandiser_list = Merchandiser.objects.filter(attivo=True).order_by('cognome')
    utenti_list = Utente.objects.filter(attivo=True).order_by('cognome')

    context = {
        'slots': slots,
        'merchandiser_list': merchandiser_list,
        'utenti_list': utenti_list,
        'filtro_merchandiser': merchandiser_id,
        'filtro_utente': utente_id,
        'solo_attivi': solo_attivi,
        'cerca': cerca,
        'oggi': oggi,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_list.html', context)


def slot_detail(request, slot_id):
    """
    Dettaglio slot con griglia orari giornalieri.

    Mostra una riga per ogni giorno nell'intervallo selezionato (parametri GET 'da' e 'a').
    Se il giorno non ha ancora una timbratura, viene creato un oggetto vuoto in memoria
    (non salvato su DB) per pre-popolare la tabella.
    """
    slot = get_object_or_404(Slot, pk=slot_id)
    oggi = timezone.now().date()

    # Lettura del filtro date dalla query string
    data_da = request.GET.get('da')
    data_a = request.GET.get('a')

    if data_da:
        try:
            data_da = datetime.strptime(data_da, '%Y-%m-%d').date()
        except:
            data_da = oggi
    else:
        data_da = oggi

    if data_a:
        try:
            data_a = datetime.strptime(data_a, '%Y-%m-%d').date()
        except:
            data_a = oggi
    else:
        data_a = oggi

    # Clamp delle date all'interno del periodo valido dello slot
    if data_da < slot.data_inizio:
        data_da = slot.data_inizio
    if data_a > slot.data_fine:
        data_a = slot.data_fine

    # Costruisci la griglia giorno per giorno nell'intervallo selezionato
    giorni = []
    current = data_da
    while current <= data_a:
        ingresso = SlotIngressoUscita.objects.filter(slot=slot, data=current).first()
        # Se non esiste una timbratura per questo giorno, crea un oggetto vuoto in memoria
        if not ingresso:
            ingresso = SlotIngressoUscita(slot=slot, data=current)
        giorni.append({
            'data': current,
            'ingresso': ingresso,
        })
        current += timedelta(days=1)

    # Calcola il totale ore lavorate nel range selezionato
    ingressi = SlotIngressoUscita.objects.filter(slot=slot, data__gte=data_da, data__lte=data_a)
    totale_ore = sum(i.ore_lavorate for i in ingressi)

    # Fornitori assegnati allo slot (relazione M2M tramite SlotFornitore)
    slot_fornitori = SlotFornitore.objects.filter(slot=slot).select_related(
        'agenzia', 'buyer', 'sotto_reparto'
    )

    # Liste per i dropdown nel form di assegnazione fornitore
    agenzie = Agenzia.objects.all().order_by('descrizione')
    buyer_list = Buyer.objects.all().order_by('nominativo')
    hostess_list = Hostess.objects.filter(attiva=True).order_by('nominativo')

    context = {
        'slot': slot,
        'giorni': giorni,
        'data_da': data_da,
        'data_a': data_a,
        'totale_ore': totale_ore,
        'slot_fornitori': slot_fornitori,
        'agenzie': agenzie,
        'hostess_list': hostess_list,
        'buyer_list': buyer_list,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_detail.html', context)


# ============================================
# SOLO ORARI (Per Punto Info)
# ============================================

def solo_orari(request):
    """
    Vista semplificata per la registrazione delle timbrature dal Punto Info.

    Mostra tutti gli slot attivi per una data specifica (default: oggi).
    Le date diverse da oggi vengono mostrate in modalità sola lettura:
    i campi orario sono disabilitati e il bottone salva non è visibile.
    """
    oggi = timezone.now().date()

    # Legge la data dalla query string; di default usa oggi
    data_str = request.GET.get('data')
    if data_str:
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            data = oggi
    else:
        data = oggi

    # Calcola i link di navigazione al giorno precedente/successivo
    data_prec = data - timedelta(days=1)
    data_succ = data + timedelta(days=1)

    # Trova tutti gli slot attivi per la data selezionata
    slots_attivi = Slot.objects.filter(
        attivo=True,
        data_inizio__lte=data,
        data_fine__gte=data
    ).select_related('merchandiser', 'utente').order_by('merchandiser__cognome')

    # Per ogni slot, recupera la timbratura esistente o crea un oggetto vuoto in memoria
    slot_orari = []
    for slot in slots_attivi:
        ingresso = SlotIngressoUscita.objects.filter(slot=slot, data=data).first()
        if not ingresso:
            ingresso = SlotIngressoUscita(slot=slot, data=data)
        slot_orari.append({
            'slot': slot,
            'ingresso': ingresso,
        })

    context = {
        'data': data,
        'data_prec': data_prec,
        'data_succ': data_succ,
        # Se la data non è oggi, la vista è in sola lettura
        'is_readonly': data != oggi,
        'slot_orari': slot_orari,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/solo_orari.html', context)


# ============================================
# API
# ============================================
@csrf_exempt
@require_http_methods(["POST"])
def salva_orario(request):
    """
    API: Salva o aggiorna l'orario di ingresso/uscita per un singolo slot/giorno.

    Riceve i dati via POST e usa get_or_create per aggiornare o creare
    il record SlotIngressoUscita. Restituisce JSON con il totale ore calcolato.
    """
    slot_id = request.POST.get('slot_id')
    data_str = request.POST.get('data')

    slot = get_object_or_404(Slot, pk=slot_id)
    data = datetime.strptime(data_str, '%Y-%m-%d').date()

    ingresso, created = SlotIngressoUscita.objects.get_or_create(
        slot=slot,
        data=data
    )

    def parse_time(val):
        """Converte una stringa 'HH:MM' in oggetto time; restituisce None se vuota o non valida."""
        if not val:
            return None
        try:
            return datetime.strptime(val, '%H:%M').time()
        except:
            return None

    # Aggiorna tutti i campi orario dal POST
    ingresso.ingresso_1 = parse_time(request.POST.get('ingresso_1'))
    ingresso.uscita_1 = parse_time(request.POST.get('uscita_1'))
    ingresso.ingresso_2 = parse_time(request.POST.get('ingresso_2'))
    ingresso.uscita_2 = parse_time(request.POST.get('uscita_2'))
    ingresso.ingresso_extra = parse_time(request.POST.get('ingresso_extra'))
    ingresso.uscita_extra = parse_time(request.POST.get('uscita_extra'))
    ingresso.forzato = request.POST.get('forzato') == 'true'
    ingresso.note = request.POST.get('note', '')

    ingresso.save()

    return JsonResponse({
        'success': True,
        'ore_lavorate': ingresso.ore_lavorate
    })


@require_http_methods(["GET"])
def cerca_fornitore(request):
    """
    API: Ricerca fornitore per nome o codice (autocomplete).

    Richiede almeno 2 caratteri nel parametro 'q'; restituisce fino a 15 risultati
    come partial HTML (usato tramite HTMX o fetch nel client).
    """
    q = request.GET.get('q', '').strip()
    # Evita query troppo corte per non caricare l'intera tabella
    if len(q) < 2:
        return render(request, 'merchandiser/partials/fornitore_results.html', {'fornitori': []})

    fornitori = Fornitore.objects.filter(
        Q(nome__icontains=q) | Q(codice__icontains=q)
    )[:15]

    return render(request, 'merchandiser/partials/fornitore_results.html', {'fornitori': fornitori})

@csrf_exempt
@require_http_methods(["POST"])
def salva_slot_fornitore(request):
    """
    API: Salva una nuova assegnazione fornitore a uno slot.

    Crea sempre un nuovo record SlotFornitore; non effettua update su record esistenti.
    I campi agenzia e buyer sono opzionali e vengono cercati per PK.
    """
    slot_id = request.POST.get('slot_id')
    slot = get_object_or_404(Slot, pk=slot_id)

    # Crea nuova assegnazione fornitore per lo slot
    sf = SlotFornitore(slot=slot)

    agenzia_id = request.POST.get('agenzia_id')
    # Se l'agenzia non viene trovata (o non è passata), il campo rimane None
    sf.agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None

    fornitore_id = request.POST.get('fornitore_id')
    sf.fornitore_id = int(fornitore_id) if fornitore_id else None

    buyer_id = request.POST.get('buyer_id')
    sf.buyer = Buyer.objects.filter(pk=buyer_id).first() if buyer_id else None

    sf.note = request.POST.get('note', '')

    sf.save()

    return JsonResponse({'success': True, 'id': sf.id})

@csrf_exempt
@require_http_methods(["POST"])
def elimina_slot_fornitore(request, sf_id):
    """API: Elimina definitivamente un'assegnazione fornitore dallo slot."""
    sf = get_object_or_404(SlotFornitore, pk=sf_id)
    sf.delete()
    return JsonResponse({'success': True})

# ============================================
# MERCHANDISER CRUD
# ============================================
def merchandiser_add(request):
    """
    Aggiunge un nuovo merchandiser.

    GET: mostra il form vuoto.
    POST: valida i dati, crea il record e restituisce JSON con i dati salvati.
    Il cognome è l'unico campo obbligatorio.
    """
    if request.method == 'POST':
        cognome = request.POST.get('cognome', '').strip()
        nome = request.POST.get('nome', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        note = request.POST.get('note', '').strip()
        attivo = request.POST.get('attivo') == 'on'

        # Validazione: il cognome è obbligatorio
        if not cognome:
            return JsonResponse({'success': False, 'error': 'Il cognome è obbligatorio'})

        merchandiser = Merchandiser.objects.create(
            cognome=cognome,
            nome=nome,
            telefono=telefono,
            email=email,
            note=note,
            attivo=attivo
        )

        return JsonResponse({
            'success': True,
            'merchandiser': {
                'id': merchandiser.id,
                'cognome': merchandiser.cognome,
                'nome': merchandiser.nome,
                'telefono': merchandiser.telefono,
                'email': merchandiser.email,
                'note': merchandiser.note,
                'attivo': merchandiser.attivo
            }
        })

    context = {
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/merchandiser_form.html', context)

def merchandiser_edit(request, merchandiser_id):
    """
    Modifica un merchandiser esistente.

    GET: mostra il form precompilato con i dati attuali.
    POST: aggiorna il record e restituisce JSON con i dati aggiornati.
    """
    merchandiser = get_object_or_404(Merchandiser, pk=merchandiser_id)

    if request.method == 'POST':
        merchandiser.cognome = request.POST.get('cognome', '').strip()
        merchandiser.nome = request.POST.get('nome', '').strip()
        merchandiser.telefono = request.POST.get('telefono', '').strip()
        merchandiser.email = request.POST.get('email', '').strip()
        merchandiser.note = request.POST.get('note', '').strip()
        merchandiser.attivo = request.POST.get('attivo') == 'on'

        # Validazione: il cognome è obbligatorio
        if not merchandiser.cognome:
            return JsonResponse({'success': False, 'error': 'Il cognome è obbligatorio'})

        merchandiser.save()

        return JsonResponse({
            'success': True,
            'merchandiser': {
                'id': merchandiser.id,
                'cognome': merchandiser.cognome,
                'nome': merchandiser.nome,
                'telefono': merchandiser.telefono,
                'email': merchandiser.email,
                'note': merchandiser.note,
                'attivo': merchandiser.attivo
            }
        })

    context = {
        'merchandiser': merchandiser,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/merchandiser_form.html', context)


@require_http_methods(["POST"])
def merchandiser_delete(request, merchandiser_id):
    """
    Soft delete di un merchandiser: imposta attivo=False invece di eliminare il record.

    Questo approccio conserva lo storico degli slot e delle timbrature associate.
    """
    merchandiser = get_object_or_404(Merchandiser, pk=merchandiser_id)
    merchandiser.attivo = False
    merchandiser.save()

    return JsonResponse({'success': True})


@require_http_methods(["POST"])
def slot_aggiorna_data_fine(request, slot_id):
    """Aggiorna solo la data fine di uno slot, mantenendo intatti tutti gli altri campi."""
    slot = get_object_or_404(Slot, pk=slot_id)
    data_fine = request.POST.get('data_fine')

    if not data_fine:
        return JsonResponse({'success': False, 'error': 'Data fine obbligatoria'})

    try:
        data_f = datetime.strptime(data_fine, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Data non valida'})

    if data_f < slot.data_inizio:
        return JsonResponse({'success': False, 'error': f'La data fine non può essere prima dell\'inizio ({slot.data_inizio.strftime("%d/%m/%Y")})'})

    slot.data_fine = data_f
    slot.save()

    return JsonResponse({'success': True, 'data_fine_display': data_f.strftime('%d/%m/%Y')})


# ============================================
# HOSTESS CRUD
# ============================================

def hostess_list(request):
    """Lista hostess con filtro opzionale sulle sole attive."""
    solo_attive = request.GET.get('attive', '1') == '1'

    hostess_qs = Hostess.objects.all().order_by('nominativo')
    if solo_attive:
        hostess_qs = hostess_qs.filter(attiva=True)

    context = {
        'hostess_list': hostess_qs,
        'solo_attive': solo_attive,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/hostess_list.html', context)


def hostess_add(request):
    """
    Aggiunge una nuova hostess.

    GET: mostra il form vuoto.
    POST: crea il record e restituisce JSON. Il nominativo è obbligatorio.
    L'ID viene calcolato manualmente come max(id)+1 perché la tabella
    Hostess è condivisa con il modulo pallet_promoter e l'auto-increment
    potrebbe collidere con sequenze già esistenti.
    """
    if request.method == 'POST':
        nominativo = request.POST.get('nominativo', '').strip()
        ruolo = request.POST.get('ruolo', '').strip()
        nota = request.POST.get('nota', '').strip()
        scadenza = request.POST.get('scadenza_libretto_sanitario', '').strip()
        attiva = request.POST.get('attiva') == 'on'

        if not nominativo:
            return JsonResponse({'success': False, 'error': 'Il nominativo è obbligatorio'})

        # Calcola il prossimo ID disponibile in modo sicuro per tabelle con ID manuale
        max_id = Hostess.objects.aggregate(models.Max('id'))['id__max'] or 0
        new_id = max_id + 1

        hostess = Hostess.objects.create(
            id=new_id,
            nominativo=nominativo,
            ruolo=ruolo,
            nota=nota,
            # Se la data è vuota, salva NULL nel DB
            scadenza_libretto_sanitario=scadenza if scadenza else None,
            attiva=attiva
        )

        return JsonResponse({
            'success': True,
            'hostess': {
                'id': hostess.id,
                'nominativo': hostess.nominativo,
                'ruolo': hostess.ruolo,
                'nota': hostess.nota,
                'scadenza_libretto_sanitario': str(hostess.scadenza_libretto_sanitario) if hostess.scadenza_libretto_sanitario else '',
                'attiva': hostess.attiva
            }
        })

    context = {
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/hostess_form.html', context)


def hostess_edit(request, hostess_id):
    """
    Modifica una hostess esistente.

    GET: mostra il form precompilato.
    POST: aggiorna il record e restituisce JSON.
    La data di scadenza del libretto sanitario viene resettata a NULL se il campo è vuoto.
    """
    hostess = get_object_or_404(Hostess, pk=hostess_id)

    if request.method == 'POST':
        hostess.nominativo = request.POST.get('nominativo', '').strip()
        hostess.ruolo = request.POST.get('ruolo', '').strip()
        hostess.nota = request.POST.get('nota', '').strip()
        scadenza = request.POST.get('scadenza_libretto_sanitario', '').strip()
        # Se il campo scadenza è vuoto, imposta NULL (reset della data)
        hostess.scadenza_libretto_sanitario = scadenza if scadenza else None
        hostess.attiva = request.POST.get('attiva') == 'on'

        if not hostess.nominativo:
            return JsonResponse({'success': False, 'error': 'Il nominativo è obbligatorio'})

        hostess.save()

        return JsonResponse({
            'success': True,
            'hostess': {
                'id': hostess.id,
                'nominativo': hostess.nominativo,
                'ruolo': hostess.ruolo,
                'nota': hostess.nota,
                'scadenza_libretto_sanitario': hostess.scadenza_libretto_sanitario.strftime('%Y-%m-%d') if hostess.scadenza_libretto_sanitario else '',
                'attiva': hostess.attiva
            }
        })

    context = {
        'hostess': hostess,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/hostess_form.html', context)


@require_http_methods(["POST"])
def hostess_delete(request, hostess_id):
    """
    Soft delete di una hostess: imposta attiva=False invece di eliminare il record.

    Conserva lo storico delle presenze associate.
    """
    hostess = get_object_or_404(Hostess, pk=hostess_id)
    hostess.attiva = False
    hostess.save()

    return JsonResponse({'success': True})

@require_http_methods(["POST"])
def salva_note_slot(request):
    """
    API: Salva le note di testo libero associate a uno slot.

    Aggiorna solo il campo 'note' dello slot senza toccare altri dati.
    Gestisce esplicitamente SlotDoesNotExist e generiche eccezioni.
    """
    slot_id = request.POST.get('slot_id')
    note = request.POST.get('note', '').strip()

    try:
        slot = Slot.objects.get(pk=slot_id)
        slot.note = note
        slot.save()

        return JsonResponse({
            'success': True,
            'note': note
        })
    except Slot.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Slot non trovato'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ============================================
# AGENZIE CRUD
# ============================================

def agenzia_list(request):
    """Lista agenzie con supporto CRUD (modifica/elimina disponibili nel template)."""
    from datetime import timedelta

    agenzie_qs = Agenzia.objects.all().order_by('descrizione')

    context = {
        'agenzie_list': agenzie_qs,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/agenzia_list.html', context)

def agenzia_add(request):
    """
    Aggiunge una nuova agenzia.

    GET: mostra il form vuoto.
    POST: valida, calcola l'ID manuale (max+1) e crea il record.
    La descrizione è obbligatoria e non può superare i 50 caratteri.
    """
    from django.db.models import Max

    if request.method == 'POST':
        descrizione = request.POST.get('descrizione', '').strip()
        nota = request.POST.get('nota', '').strip()

        # Validazione descrizione: obbligatoria e max 50 caratteri
        if not descrizione:
            return JsonResponse({
                'success': False,
                'error': 'La descrizione è obbligatoria'
            })

        if len(descrizione) > 50:
            return JsonResponse({
                'success': False,
                'error': 'La descrizione non può superare i 50 caratteri'
            })

        # Calcola il prossimo ID disponibile (la tabella usa ID manuale)
        max_id = Agenzia.objects.aggregate(Max('id'))['id__max'] or 0
        next_id = max_id + 1

        # Crea agenzia con ID assegnato manualmente
        agenzia = Agenzia.objects.create(
            id=next_id,
            descrizione=descrizione,
            nota=nota if nota else None
        )

        return JsonResponse({
            'success': True,
            'agenzia': {
                'id': agenzia.id,
                'descrizione': agenzia.descrizione,
                'nota': agenzia.nota
            }
        })

    context = {
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/agenzia_form.html', context)

def agenzia_edit(request, agenzia_id):
    """
    Modifica un'agenzia esistente.

    GET: mostra il form precompilato.
    POST: aggiorna descrizione e nota con validazione lunghezza.
    """
    agenzia = get_object_or_404(Agenzia, pk=agenzia_id)

    if request.method == 'POST':
        descrizione = request.POST.get('descrizione', '').strip()
        nota = request.POST.get('nota', '').strip()

        # Validazione descrizione
        if not descrizione:
            return JsonResponse({
                'success': False,
                'error': 'La descrizione è obbligatoria'
            })

        if len(descrizione) > 50:
            return JsonResponse({
                'success': False,
                'error': 'La descrizione non può superare i 50 caratteri'
            })

        # Aggiorna i campi e salva
        agenzia.descrizione = descrizione
        agenzia.nota = nota if nota else None
        agenzia.save()

        return JsonResponse({
            'success': True,
            'agenzia': {
                'id': agenzia.id,
                'descrizione': agenzia.descrizione,
                'nota': agenzia.nota
            }
        })

    context = {
        'agenzia': agenzia,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/agenzia_form.html', context)


@require_http_methods(["POST"])
def agenzia_delete(request, agenzia_id):
    """
    Elimina definitivamente un'agenzia dal database.

    A differenza di merchandiser e hostess, le agenzie vengono eliminate
    con hard delete (delete()) e non con soft delete.
    """
    agenzia = get_object_or_404(Agenzia, pk=agenzia_id)
    agenzia.delete()

    return JsonResponse({'success': True})

def slot_add(request):
    """
    Aggiunge un nuovo slot di lavoro per un merchandiser.

    GET: mostra il form vuoto con la lista dei merchandiser attivi.
    POST: valida le date (data_fine >= data_inizio), legge i giorni lavorativi
    dai checkbox e crea il record Slot.
    """
    if request.method == 'POST':
        merchandiser_id = request.POST.get('merchandiser_id')
        data_inizio = request.POST.get('data_inizio')
        data_fine = request.POST.get('data_fine')
        plafond_ore = request.POST.get('plafond_ore', 0)
        badge = request.POST.get('badge', '').strip()
        note = request.POST.get('note', '').strip()

        # Lettura dei giorni lavorativi dai checkbox del form
        lun = request.POST.get('lun') == 'on'
        mar = request.POST.get('mar') == 'on'
        mer = request.POST.get('mer') == 'on'
        gio = request.POST.get('gio') == 'on'
        ven = request.POST.get('ven') == 'on'
        sab = request.POST.get('sab') == 'on'
        dom = request.POST.get('dom') == 'on'

        # Validazione campi obbligatori
        if not merchandiser_id:
            return JsonResponse({'success': False, 'error': 'Seleziona un merchandiser'})

        if not data_inizio or not data_fine:
            return JsonResponse({'success': False, 'error': 'Inserisci data inizio e fine'})

        try:
            data_i = datetime.strptime(data_inizio, '%Y-%m-%d').date()
            data_f = datetime.strptime(data_fine, '%Y-%m-%d').date()

            # La data di fine deve essere uguale o successiva alla data di inizio
            if data_f < data_i:
                return JsonResponse({'success': False, 'error': 'La data fine deve essere >= data inizio'})
        except:
            return JsonResponse({'success': False, 'error': 'Date non valide'})

        # Crea lo slot con tutti i campi
        slot = Slot.objects.create(
            merchandiser_id=merchandiser_id,
            data_inizio=data_i,
            data_fine=data_f,
            lun=lun, mar=mar, mer=mer, gio=gio, ven=ven, sab=sab, dom=dom,
            plafond_ore=plafond_ore,
            badge=badge if badge else None,
            note=note if note else None
        )

        return JsonResponse({'success': True, 'slot_id': slot.id})

    # GET: carica solo i merchandiser attivi per il dropdown
    merchandiser_list = Merchandiser.objects.filter(attivo=True).order_by('cognome')

    context = {
        'merchandiser_list': merchandiser_list,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_form.html', context)

def slot_edit(request, slot_id):
    """
    Modifica uno slot esistente.

    GET: mostra il form precompilato con i dati attuali dello slot.
    POST: aggiorna tutti i campi con la stessa logica di slot_add.
    """
    slot = get_object_or_404(Slot, pk=slot_id)

    if request.method == 'POST':
        merchandiser_id = request.POST.get('merchandiser_id')
        data_inizio = request.POST.get('data_inizio')
        data_fine = request.POST.get('data_fine')
        plafond_ore = request.POST.get('plafond_ore', 0)
        badge = request.POST.get('badge', '').strip()
        note = request.POST.get('note', '').strip()

        # Lettura dei giorni lavorativi dai checkbox del form
        lun = request.POST.get('lun') == 'on'
        mar = request.POST.get('mar') == 'on'
        mer = request.POST.get('mer') == 'on'
        gio = request.POST.get('gio') == 'on'
        ven = request.POST.get('ven') == 'on'
        sab = request.POST.get('sab') == 'on'
        dom = request.POST.get('dom') == 'on'

        # Validazione campi obbligatori
        if not merchandiser_id:
            return JsonResponse({'success': False, 'error': 'Seleziona un merchandiser'})

        if not data_inizio or not data_fine:
            return JsonResponse({'success': False, 'error': 'Inserisci data inizio e fine'})

        try:
            data_i = datetime.strptime(data_inizio, '%Y-%m-%d').date()
            data_f = datetime.strptime(data_fine, '%Y-%m-%d').date()

            if data_f < data_i:
                return JsonResponse({'success': False, 'error': 'La data fine deve essere >= data inizio'})
        except:
            return JsonResponse({'success': False, 'error': 'Date non valide'})

        # Aggiorna tutti i campi dello slot
        slot.merchandiser_id = merchandiser_id
        slot.data_inizio = data_i
        slot.data_fine = data_f
        slot.lun = lun
        slot.mar = mar
        slot.mer = mer
        slot.gio = gio
        slot.ven = ven
        slot.sab = sab
        slot.dom = dom
        slot.plafond_ore = plafond_ore
        slot.badge = badge if badge else None
        slot.note = note if note else None
        slot.save()

        return JsonResponse({'success': True, 'slot_id': slot.id})

    # GET: carica lista merchandiser attivi per il dropdown
    merchandiser_list = Merchandiser.objects.filter(attivo=True).order_by('cognome')

    context = {
        'slot': slot,
        'merchandiser_list': merchandiser_list,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_form.html', context)


@require_http_methods(["POST"])
def slot_delete(request, slot_id):
    """
    Soft delete di uno slot: imposta attivo=False senza eliminare il record.

    Le timbrature già registrate per lo slot vengono conservate nel database.
    """
    slot = get_object_or_404(Slot, pk=slot_id)

    slot.attivo = False
    slot.save()

    return JsonResponse({'success': True})

@require_http_methods(["POST"])
def slot_restore(request, slot_id):
    """
    Riattiva uno slot precedentemente disattivato con soft delete.

    Imposta attivo=True rendendo lo slot nuovamente visibile nelle liste e nella dashboard.
    """
    slot = get_object_or_404(Slot, pk=slot_id)
    slot.attivo = True
    slot.save()

    return JsonResponse({'success': True})
