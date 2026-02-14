from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.db import models

from .models import (
    Attivita, Utente, Merchandiser, Slot, SlotFornitore, SlotIngressoUscita
)
from modules.pallet_promoter.models import Agenzia, Fornitore, Buyer, Hostess, PresenzaHostess


def get_current_user(request):
    """Recupera l'utente corrente dall'header LDAP."""
    return request.META.get('HTTP_X_REMOTE_USER', 'anonymous')


# ============================================
# DASHBOARD
# ============================================

def index(request):
    """Dashboard principale Merchandiser."""
    oggi = timezone.now().date()
    
    # Statistiche
    merchandiser_attivi = Merchandiser.objects.filter(attivo=True).count()
    slot_attivi = Slot.objects.filter(data_inizio__lte=oggi, data_fine__gte=oggi).count()
    timbrature_oggi = SlotIngressoUscita.objects.filter(data=oggi).count()
    attivita_count = Attivita.objects.count()
    
    # Slot attivi oggi
    slot_oggi = Slot.objects.filter(
        data_inizio__lte=oggi,
        data_fine__gte=oggi
    ).select_related('merchandiser', 'utente')[:10]
    
    context = {
        'merchandiser_attivi': merchandiser_attivi,
        'slot_attivi': slot_attivi,
        'timbrature_oggi': timbrature_oggi,
        'attivita_count': attivita_count,
        'slot_oggi': slot_oggi,
        'oggi': oggi,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/index.html', context)


# ============================================
# MERCHANDISER (Anagrafica)
# ============================================

def merchandiser_list(request):
    """Lista merchandiser."""
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
# ATTIVITA
# ============================================

def attivita_list(request):
    """Lista attività."""
    attivita = Attivita.objects.all().order_by('id')
    
    context = {
        'attivita_list': attivita,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/attivita_list.html', context)


# ============================================
# UTENTI (Referenti)
# ============================================

def utenti_list(request):
    """Lista utenti/referenti."""
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
    """Lista agenzie."""
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
    """Lista slot con filtri."""
    oggi = timezone.now().date()
    
    # Filtri
    merchandiser_id = request.GET.get('merchandiser')
    utente_id = request.GET.get('utente')
    solo_attivi = request.GET.get('attivi', '1') == '1'
    
    slots = Slot.objects.all().select_related('merchandiser', 'utente')
    
    if merchandiser_id:
        slots = slots.filter(merchandiser_id=merchandiser_id)
    if utente_id:
        slots = slots.filter(utente_id=utente_id)
    if solo_attivi:
        slots = slots.filter(
            attivo=True,
            data_inizio__lte=oggi,   # Già iniziato ✅
            data_fine__gte=oggi      # Non ancora finito ✅
    )
    
    slots = slots.order_by('merchandiser__cognome', 'merchandiser__nome', '-data_inizio')[:100]
    
    for s in slots[:3]:  # Mostra primi 3
        print(f"    Slot {s.id}: attivo={s.attivo}, data_fine={s.data_fine}")
    
    # Liste per filtri
    merchandiser_list = Merchandiser.objects.filter(attivo=True).order_by('cognome')
    utenti_list = Utente.objects.filter(attivo=True).order_by('cognome')
    
    context = {
        'slots': slots,
        'merchandiser_list': merchandiser_list,
        'utenti_list': utenti_list,
        'filtro_merchandiser': merchandiser_id,
        'filtro_utente': utente_id,
        'solo_attivi': solo_attivi,
        'oggi': oggi,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_list.html', context)


def slot_detail(request, slot_id):
    """Dettaglio slot con griglia orari."""
    slot = get_object_or_404(Slot, pk=slot_id)
    oggi = timezone.now().date()
    
    # Filtro date per griglia orari
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
    
    # Limita alle date del periodo slot
    if data_da < slot.data_inizio:
        data_da = slot.data_inizio
    if data_a > slot.data_fine:
        data_a = slot.data_fine
    
    # Costruisci griglia giorni
    giorni = []
    current = data_da
    while current <= data_a:
        ingresso = SlotIngressoUscita.objects.filter(slot=slot, data=current).first()
        if not ingresso:
            ingresso = SlotIngressoUscita(slot=slot, data=current)
        giorni.append({
            'data': current,
            'ingresso': ingresso,
        })
        current += timedelta(days=1)
    
    # Calcola totale ore nel range
    ingressi = SlotIngressoUscita.objects.filter(slot=slot, data__gte=data_da, data__lte=data_a)
    totale_ore = sum(i.ore_lavorate for i in ingressi)
    
    # Fornitori assegnati allo slot
    slot_fornitori = SlotFornitore.objects.filter(slot=slot).select_related(
        'agenzia', 'attivita', 'buyer', 'sotto_reparto'
    )
    
    # Liste per dropdown
    agenzie = Agenzia.objects.all().order_by('descrizione')
    attivita = Attivita.objects.all().order_by('descrizione')
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
        'attivita': attivita,
        'hostess_list': hostess_list,
        'buyer_list': buyer_list,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_detail.html', context)


# ============================================
# SOLO ORARI (Per Punto Info)
# ============================================

def solo_orari(request):
    """Vista semplificata per timbrature - Punto Info."""
    oggi = timezone.now().date()
    
    # Filtro data
    data_str = request.GET.get('data')
    if data_str:
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except:
            data = oggi
    else:
        data = oggi
    
    # Date per navigazione
    data_prec = data - timedelta(days=1)
    data_succ = data + timedelta(days=1)
    
    # Trova tutti gli slot attivi per questa data
    slots_attivi = Slot.objects.filter(
        attivo=True, 
        data_inizio__lte=data,
        data_fine__gte=data
    ).select_related('merchandiser', 'utente').order_by('merchandiser__cognome')
    
    # Per ogni slot, prendi o crea l'ingresso/uscita
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
    """Salva orario singolo slot/giorno."""
    slot_id = request.POST.get('slot_id')
    data_str = request.POST.get('data')
    
    slot = get_object_or_404(Slot, pk=slot_id)
    data = datetime.strptime(data_str, '%Y-%m-%d').date()
    
    ingresso, created = SlotIngressoUscita.objects.get_or_create(
        slot=slot,
        data=data
    )
    
    def parse_time(val):
        if not val:
            return None
        try:
            return datetime.strptime(val, '%H:%M').time()
        except:
            return None
    
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
    """Ricerca fornitore per autocomplete."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return render(request, 'merchandiser/partials/fornitore_results.html', {'fornitori': []})
    
    fornitori = Fornitore.objects.filter(
        Q(nome__icontains=q) | Q(codice__icontains=q)
    )[:15]
    
    return render(request, 'merchandiser/partials/fornitore_results.html', {'fornitori': fornitori})

@csrf_exempt
@require_http_methods(["POST"])
def salva_slot_fornitore(request):
    """Salva assegnazione fornitore a slot."""
    slot_id = request.POST.get('slot_id')
    slot = get_object_or_404(Slot, pk=slot_id)
    
    # Crea nuova assegnazione
    sf = SlotFornitore(slot=slot)
    
    agenzia_id = request.POST.get('agenzia_id')
    sf.agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None
    
    fornitore_id = request.POST.get('fornitore_id')
    sf.fornitore_id = int(fornitore_id) if fornitore_id else None
    
    attivita_id = request.POST.get('attivita_id')
    sf.attivita = Attivita.objects.filter(pk=attivita_id).first() if attivita_id else None
    
    buyer_id = request.POST.get('buyer_id')
    sf.buyer = Buyer.objects.filter(pk=buyer_id).first() if buyer_id else None
    
    sf.note = request.POST.get('note', '')
    
    sf.save()
    
    return JsonResponse({'success': True, 'id': sf.id})

@csrf_exempt
@require_http_methods(["POST"])
def elimina_slot_fornitore(request, sf_id):
    """Elimina assegnazione fornitore."""
    sf = get_object_or_404(SlotFornitore, pk=sf_id)
    sf.delete()
    return JsonResponse({'success': True})
# ============================================
# MERCHANDISER CRUD
# ============================================

def merchandiser_add(request):
    """Aggiungi nuovo merchandiser."""
    if request.method == 'POST':
        cognome = request.POST.get('cognome', '').strip()
        nome = request.POST.get('nome', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        note = request.POST.get('note', '').strip()
        attivo = request.POST.get('attivo') == 'on'
        
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
    """Modifica merchandiser esistente."""
    merchandiser = get_object_or_404(Merchandiser, pk=merchandiser_id)
    
    if request.method == 'POST':
        merchandiser.cognome = request.POST.get('cognome', '').strip()
        merchandiser.nome = request.POST.get('nome', '').strip()
        merchandiser.telefono = request.POST.get('telefono', '').strip()
        merchandiser.email = request.POST.get('email', '').strip()
        merchandiser.note = request.POST.get('note', '').strip()
        merchandiser.attivo = request.POST.get('attivo') == 'on'
        
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


@csrf_exempt
@require_http_methods(["POST"])
def merchandiser_delete(request, merchandiser_id):
    """Elimina (soft delete) merchandiser."""
    merchandiser = get_object_or_404(Merchandiser, pk=merchandiser_id)
    merchandiser.attivo = False
    merchandiser.save()
    
    return JsonResponse({'success': True})


# ============================================
# HOSTESS CRUD
# ============================================

def hostess_list(request):
    """Lista hostess."""
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
    """Aggiungi nuova hostess."""
    if request.method == 'POST':
        nominativo = request.POST.get('nominativo', '').strip()
        ruolo = request.POST.get('ruolo', '').strip()
        nota = request.POST.get('nota', '').strip()
        scadenza = request.POST.get('scadenza_libretto_sanitario', '').strip()
        attiva = request.POST.get('attiva') == 'on'
        
        if not nominativo:
            return JsonResponse({'success': False, 'error': 'Il nominativo è obbligatorio'})
        
        # Trova ID disponibile
        max_id = Hostess.objects.aggregate(models.Max('id'))['id__max'] or 0
        new_id = max_id + 1
        
        hostess = Hostess.objects.create(
            id=new_id,
            nominativo=nominativo,
            ruolo=ruolo,
            nota=nota,
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
    """Modifica hostess esistente."""
    hostess = get_object_or_404(Hostess, pk=hostess_id)
    
    if request.method == 'POST':
        hostess.nominativo = request.POST.get('nominativo', '').strip()
        hostess.ruolo = request.POST.get('ruolo', '').strip()
        hostess.nota = request.POST.get('nota', '').strip()
        scadenza = request.POST.get('scadenza_libretto_sanitario', '').strip()
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


@csrf_exempt
@require_http_methods(["POST"])
def hostess_delete(request, hostess_id):
    """Elimina (soft delete) hostess."""
    hostess = get_object_or_404(Hostess, pk=hostess_id)
    hostess.attiva = False
    hostess.save()
    
    return JsonResponse({'success': True})
@csrf_exempt
@require_http_methods(["POST"])
def salva_note_slot(request):
    """Salva note dello slot."""
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
    """Lista agenzie."""
    from datetime import timedelta
    
    agenzie_qs = Agenzia.objects.all().order_by('descrizione')
    
    context = {
        'agenzie_list': agenzie_qs,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/agenzia_list.html', context)

@csrf_exempt
def agenzia_add(request):
    """Aggiungi agenzia."""
    from django.db.models import Max
    
    if request.method == 'POST':
        descrizione = request.POST.get('descrizione', '').strip()
        nota = request.POST.get('nota', '').strip()
        
        # Validazione
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
        
        # Calcola prossimo ID
        max_id = Agenzia.objects.aggregate(Max('id'))['id__max'] or 0
        next_id = max_id + 1
        
        # Crea agenzia con ID manuale
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

@csrf_exempt
def agenzia_edit(request, agenzia_id):
    """Modifica agenzia."""
    agenzia = get_object_or_404(Agenzia, pk=agenzia_id)
    
    if request.method == 'POST':
        descrizione = request.POST.get('descrizione', '').strip()
        nota = request.POST.get('nota', '').strip()
        
        # Validazione
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
        
        # Aggiorna
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


@csrf_exempt
@require_http_methods(["POST"])
def agenzia_delete(request, agenzia_id):
    """Elimina agenzia."""
    agenzia = get_object_or_404(Agenzia, pk=agenzia_id)
    agenzia.delete()
    
    return JsonResponse({'success': True})

@csrf_exempt
def slot_add(request):
    """Aggiungi nuovo slot."""
    if request.method == 'POST':
        merchandiser_id = request.POST.get('merchandiser_id')
        data_inizio = request.POST.get('data_inizio')
        data_fine = request.POST.get('data_fine')
        plafond_ore = request.POST.get('plafond_ore', 0)
        badge = request.POST.get('badge', '').strip()
        note = request.POST.get('note', '').strip()
        
        # Giorni
        lun = request.POST.get('lun') == 'on'
        mar = request.POST.get('mar') == 'on'
        mer = request.POST.get('mer') == 'on'
        gio = request.POST.get('gio') == 'on'
        ven = request.POST.get('ven') == 'on'
        sab = request.POST.get('sab') == 'on'
        dom = request.POST.get('dom') == 'on'
        
        # Validazione
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
        
        # Crea slot
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
    
    # GET
    merchandiser_list = Merchandiser.objects.filter(attivo=True).order_by('cognome')
    
    context = {
        'merchandiser_list': merchandiser_list,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_form.html', context)

@csrf_exempt
def slot_edit(request, slot_id):
    """Modifica slot."""
    slot = get_object_or_404(Slot, pk=slot_id)
    
    if request.method == 'POST':
        merchandiser_id = request.POST.get('merchandiser_id')
        data_inizio = request.POST.get('data_inizio')
        data_fine = request.POST.get('data_fine')
        plafond_ore = request.POST.get('plafond_ore', 0)
        badge = request.POST.get('badge', '').strip()
        note = request.POST.get('note', '').strip()
        
        # Giorni
        lun = request.POST.get('lun') == 'on'
        mar = request.POST.get('mar') == 'on'
        mer = request.POST.get('mer') == 'on'
        gio = request.POST.get('gio') == 'on'
        ven = request.POST.get('ven') == 'on'
        sab = request.POST.get('sab') == 'on'
        dom = request.POST.get('dom') == 'on'
        
        # Validazione
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
        
        # Aggiorna
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
    
    # GET
    merchandiser_list = Merchandiser.objects.filter(attivo=True).order_by('cognome')
    
    context = {
        'slot': slot,
        'merchandiser_list': merchandiser_list,
        'current_user': get_current_user(request),
    }
    return render(request, 'merchandiser/slot_form.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def slot_delete(request, slot_id):
    """Disattiva slot (soft delete)."""
    
    slot = get_object_or_404(Slot, pk=slot_id)
    
    slot.attivo = False
    slot.save()
    
    return JsonResponse({'success': True})
@csrf_exempt
@require_http_methods(["POST"])
def slot_restore(request, slot_id):
    """Riattiva slot (annulla soft delete)."""
    slot = get_object_or_404(Slot, pk=slot_id)
    slot.attivo = True
    slot.save()
    
    return JsonResponse({'success': True})