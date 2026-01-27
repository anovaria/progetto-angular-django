from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Attivita, Utente, Merchandiser, Slot, SlotFornitore, SlotIngressoUscita, SottoReparto
)
from modules.pallet_promoter.models import Agenzia, Fornitore, Buyer


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
        slots = slots.filter(data_fine__gte=oggi)
    
    slots = slots.order_by('-data_inizio')[:100]
    
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
    
    context = {
        'slot': slot,
        'giorni': giorni,
        'data_da': data_da,
        'data_a': data_a,
        'totale_ore': totale_ore,
        'slot_fornitori': slot_fornitori,
        'agenzie': agenzie,
        'attivita': attivita,
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


@require_http_methods(["POST"])
def elimina_slot_fornitore(request, sf_id):
    """Elimina assegnazione fornitore."""
    sf = get_object_or_404(SlotFornitore, pk=sf_id)
    sf.delete()
    return JsonResponse({'success': True})
