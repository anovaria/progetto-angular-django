from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt


from .models import (
    Periodo, Pallet, Testata, Fornitore, Buyer, Agenzia,
    AssegnazionePallet, AssegnazioneTestata,
    Hostess, PianificazioneHostess, PresenzaHostess,
    UtenteBuyer
)


def get_current_user(request):
    """
    Recupera l'utente corrente dal request.
    Compatibile con Windows Auth e JWT.
    """
    username = None
    
    # DEBUG - rimuovi dopo
    print(f"DEBUG META keys: {[k for k in request.META.keys() if 'USER' in k or 'AUTH' in k]}")
    print(f"DEBUG request.user: {request.user}, authenticated: {request.user.is_authenticated if hasattr(request, 'user') else 'N/A'}")
    print(f"DEBUG request.user: {getattr(request, 'user', 'NO USER')}")
    print(f"DEBUG is_authenticated: {request.user.is_authenticated if hasattr(request, 'user') else 'N/A'}")
    print(f"DEBUG REMOTE_USER: {request.META.get('REMOTE_USER', 'NONE')}")

    # Windows Auth
    if hasattr(request, 'META') and 'REMOTE_USER' in request.META:
        username = request.META['REMOTE_USER'].split('\\')[-1].lower()
    
    # JWT / Dev
    if not username and hasattr(request, 'user') and request.user.is_authenticated:
        username = request.user.username.lower()
    
    print(f"DEBUG username finale: {username}")


# ============================================
# DASHBOARD
# ============================================

def index(request):
    """Dashboard principale Pallet-Promoter."""
    oggi = timezone.now().date()
    
    # Periodo corrente
    periodo_corrente = Periodo.objects.filter(
        data_inizio__lte=oggi,
        data_fine__gte=oggi
    ).first()
    
    # Prossimi periodi
    prossimi_periodi = Periodo.objects.filter(
        data_inizio__gt=oggi
    ).order_by('data_inizio')[:5]
    
    # Statistiche
    stats = {
        'totale_pallet': Pallet.objects.count(),
        'totale_testate': Testata.objects.count(),
        'totale_fornitori': Fornitore.objects.count(),
        'totale_hostess': Hostess.objects.filter(attiva=True).count(),
    }
    
    context = {
        'periodo_corrente': periodo_corrente,
        'prossimi_periodi': prossimi_periodi,
        'stats': stats,
        'current_user': get_current_user(request),
    }
    return render(request, 'pallet_promoter/index.html', context)


# ============================================
# PALLET
# ============================================

def pallet_list(request):
    """Lista periodi per selezione."""
    anno_corrente = timezone.now().year
    anno_selezionato = int(request.GET.get('anno', anno_corrente))
    periodi = Periodo.objects.filter(anno=anno_selezionato).order_by('data_inizio')
    
    # Anni disponibili per filtro
    anni = Periodo.objects.values_list('anno', flat=True).distinct().order_by('-anno')
    
    context = {
        'periodi': periodi,
        'anni': anni,
        'anno_selezionato': anno_selezionato,
        'today': timezone.now().date(),
    }
    return render(request, 'pallet_promoter/pallet_list.html', context)


def pallet_griglia(request, periodo_id):
    """Griglia assegnazioni pallet per un periodo."""
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    current_user = get_current_user(request)
    
    # Buyer disponibili per l'utente
    buyer_utente = UtenteBuyer.get_buyer_per_utente(current_user)
    is_admin = UtenteBuyer.is_admin(current_user)
    
    if is_admin:
        # Admin vede tutti i buyer
        buyer_list = Buyer.objects.exclude(nominativo__isnull=True).exclude(nominativo='').order_by('nominativo')
    else:
        # Utente vede solo i suoi buyer
        buyer_list = buyer_utente.exclude(nominativo__isnull=True).exclude(nominativo='').order_by('nominativo')    
    # Buyer selezionato (da query string o primo disponibile)
    buyer_id = request.GET.get('buyer')
    if buyer_id:
        buyer_selezionato = Buyer.objects.filter(pk=buyer_id).first()
        # Verifica che l'utente abbia accesso a questo buyer
        if not is_admin and buyer_selezionato not in buyer_list:
            buyer_selezionato = buyer_list.first()
    else:
        buyer_selezionato = buyer_list.first()
    
    # Se l'utente ha un solo buyer, selezionalo automaticamente
    mostra_dropdown = is_admin or buyer_list.count() > 1
    
    # Pallet e assegnazioni per il buyer selezionato
    pallet_per_buyer = {}
    if buyer_selezionato:
        pallet = Pallet.objects.filter(buyer=buyer_selezionato).order_by('codice')
        assegnazioni = {}
        
        for p in pallet:
            assegn = AssegnazionePallet.objects.filter(
                periodo=periodo, pallet=p
            ).first()
            assegnazioni[p.id] = assegn
        
        if pallet.exists():
            pallet_per_buyer[buyer_selezionato] = {
                'pallet': pallet,
                'assegnazioni': assegnazioni,
            }
    if is_admin:
    # Admin vede tutti i buyer
        buyer_list = list(Buyer.objects.exclude(nominativo__isnull=True).exclude(nominativo='').order_by('nominativo'))
    else:
    # Utente vede solo i suoi buyer
        buyer_list = list(buyer_utente.exclude(nominativo__isnull=True).exclude(nominativo='').order_by('nominativo'))
    for buyer in buyer_list:
        buyer.is_selected = (buyer_selezionato and buyer.id == buyer_selezionato.id)

    context = {
        'periodo': periodo,
        'pallet_per_buyer': pallet_per_buyer,
        'buyer_list': buyer_list,
        'buyer_selezionato': buyer_selezionato,
        'mostra_dropdown': mostra_dropdown,
        'is_admin': is_admin,
        'current_user': current_user,
    }
    return render(request, 'pallet_promoter/pallet_griglia.html', context)


# ============================================
# TESTATE
# ============================================

def testate_list(request):
    """Lista mesi/anni per selezione testate."""
    anno_corrente = timezone.now().year
    mese_corrente = timezone.now().month
    
    context = {
        'anno': anno_corrente,
        'mese': mese_corrente,
        'mesi': range(1, 13),
        'anni': range(anno_corrente - 1, anno_corrente + 2),
    }
    return render(request, 'pallet_promoter/testate_list.html', context)


def testate_griglia(request, anno, mese):
    """Griglia assegnazioni testate per mese/anno."""
    testate = Testata.objects.all().order_by('id')
    
    assegnazioni = {}
    for t in testate:
        assegn = AssegnazioneTestata.objects.filter(
            testata=t, anno=anno, mese=mese
        ).first()
        assegnazioni[t.id] = assegn
    
    context = {
        'anno': anno,
        'mese': mese,
        'testate': testate,
        'assegnazioni': assegnazioni,
        'current_user': get_current_user(request),
    }
    return render(request, 'pallet_promoter/testate_griglia.html', context)


# ============================================
# HOSTESS
# ============================================

def hostess_planning(request):
    """Planning settimanale hostess - Individuazione Hostess."""
    from datetime import timedelta
    
    # Trova il periodo corrente o selezionato
    oggi = timezone.now().date()
    periodo_id = request.GET.get('periodo')
    
    if periodo_id:
        periodo = Periodo.objects.filter(pk=periodo_id).first()
    else:
        periodo = Periodo.objects.filter(
            data_inizio__lte=oggi,
            data_fine__gte=oggi
        ).first()
    
    if not periodo:
        # Prendi il prossimo periodo
        periodo = Periodo.objects.filter(data_inizio__gt=oggi).order_by('data_inizio').first()
    
    if not periodo:
        return render(request, 'pallet_promoter/hostess_no_periodo.html')
    
    # Giorno selezionato (default: oggi se nel periodo, altrimenti primo giorno)
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
    
    # Assicurati che il giorno sia nel periodo
    if giorno < periodo.data_inizio:
        giorno = periodo.data_inizio
    elif giorno > periodo.data_fine:
        giorno = periodo.data_fine
    
    # Giorni precedente e successivo per navigazione
    giorno_prec = giorno - timedelta(days=1) if giorno > periodo.data_inizio else None
    giorno_succ = giorno + timedelta(days=1) if giorno < periodo.data_fine else None
    
    # Numero slot attivi (da NHostess del periodo, max 13)
    num_slots = min(periodo.num_hostess or 12, 13)
    
    # Carica presenze per il giorno selezionato
    presenze = {}
    for slot in range(1, num_slots + 1):
        presenza = PresenzaHostess.objects.filter(giorno=giorno, slot=slot).first()
        if not presenza:
            # Crea oggetto vuoto (non salvato)
            presenza = PresenzaHostess(giorno=giorno, slot=slot)
        presenze[slot] = presenza
    
    # Lista giorni del periodo per la griglia in basso
    giorni_periodo = []
    current = periodo.data_inizio
    while current <= periodo.data_fine:
        # Carica riepilogo per ogni giorno
        presenze_giorno = PresenzaHostess.objects.filter(giorno=current).select_related('hostess', 'fornitore', 'agenzia')
        giorni_periodo.append({
            'data': current,
            'presenze': list(presenze_giorno),
        })
        current += timedelta(days=1)
    
    # Liste per dropdown
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
    """Lista presenze/timbrature."""
    oggi = timezone.now().date()
    
    presenze = PresenzaHostess.objects.filter(
        giorno=oggi
    ).select_related('hostess', 'agenzia').order_by('slot')
    
    context = {
        'presenze': presenze,
        'giorno': oggi,
    }
    return render(request, 'pallet_promoter/presenze_list.html', context)


def scelta_fornitore_hostess(request):
    """Scelta Fornitore per Hostess - Griglia settimanale."""
    from datetime import timedelta
    
    oggi = timezone.now().date()
    periodo_id = request.GET.get('periodo')
    
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
        return render(request, 'pallet_promoter/hostess_no_periodo.html')
    
    # Numero slot
    num_slots = min(periodo.num_hostess or 12, 13)
    
    # Costruisci griglia giorni
    giorni = []
    current = periodo.data_inizio
    while current <= periodo.data_fine:
        presenze_giorno = {}
        for slot in range(1, num_slots + 1):
            presenza = PresenzaHostess.objects.filter(giorno=current, slot=slot).select_related('fornitore').first()
            presenze_giorno[slot] = presenza
        
        giorni.append({
            'data': current,
            'presenze': presenze_giorno,
        })
        current += timedelta(days=1)
    
    # Lista periodi per sidebar
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
    """Assegna un pallet a un fornitore (HTMX)."""
    pallet_id = request.POST.get('pallet_id')
    periodo_id = request.POST.get('periodo_id')
    fornitore_id = request.POST.get('fornitore_id')
    dettaglio = request.POST.get('dettaglio', '')
    
    pallet = get_object_or_404(Pallet, pk=pallet_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    fornitore = Fornitore.objects.filter(pk=fornitore_id).first() if fornitore_id else None
    
    assegn, created = AssegnazionePallet.objects.update_or_create(
        pallet=pallet,
        periodo=periodo,
        defaults={
            'fornitore': fornitore,
            'dettaglio': dettaglio,
            'modificato_da': get_current_user(request),
        }
    )
    
    # Ritorna il fragment HTML aggiornato
    return render(request, 'pallet_promoter/partials/pallet_cell.html', {
        'pallet': pallet,
        'assegnazione': assegn,
        'periodo': periodo,
    })


@require_http_methods(["POST"])
def assegna_testata(request):
    """Assegna una testata a un fornitore (HTMX)."""
    testata_id = request.POST.get('testata_id')
    anno = int(request.POST.get('anno'))
    mese = int(request.POST.get('mese'))
    fornitore_id = request.POST.get('fornitore_id')
    
    testata = get_object_or_404(Testata, pk=testata_id)
    fornitore = Fornitore.objects.filter(pk=fornitore_id).first() if fornitore_id else None
    utente = get_current_user(request)
    
    assegn, created = AssegnazioneTestata.objects.update_or_create(
        testata=testata,
        anno=anno,
        mese=mese,
        defaults={
            'fornitore': fornitore,
            'modificato_da': utente,
        }
    )
    
    # Aggiorna log
    if fornitore:
        azione = f"AGGIUNTA TESTATA: {testata.id}-{fornitore.codice}-{fornitore.nome}"
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
    """Salva una presenza hostess."""
    import json
    from datetime import datetime
    
    giorno_str = request.POST.get('giorno')
    slot = int(request.POST.get('slot'))
    
    giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()
    
    # Recupera o crea la presenza
    presenza, created = PresenzaHostess.objects.get_or_create(
        giorno=giorno,
        slot=slot,
        defaults={'tipo': 'STD'}
    )
    
    # Aggiorna campi
    fornitore_id = request.POST.get('fornitore_id')
    presenza.fornitore = Fornitore.objects.filter(pk=fornitore_id).first() if fornitore_id else None
    presenza.nota_fornitore = request.POST.get('nota_fornitore', '')
    
    hostess_id = request.POST.get('hostess_id')
    presenza.hostess = Hostess.objects.filter(pk=hostess_id).first() if hostess_id else None
    
    agenzia_id = request.POST.get('agenzia_id')
    presenza.agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None
    
    # Orari
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

@csrf_exempt
@require_http_methods(["POST"])
def salva_tutte_presenze(request):
    """Salva tutte le presenze di un giorno."""
    import json
    from datetime import datetime
    
    data = json.loads(request.body)
    giorno_str = data.get('giorno')
    presenze_data = data.get('presenze', [])
    
    giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()
    
    saved = 0
    for p in presenze_data:
        slot = int(p.get('slot'))
        
        presenza, created = PresenzaHostess.objects.get_or_create(
            giorno=giorno,
            slot=slot,
            defaults={'tipo': 'STD'}
        )
        
        # Aggiorna campi
        fornitore_id = p.get('fornitore_id')
        presenza.fornitore = Fornitore.objects.filter(pk=fornitore_id).first() if fornitore_id else None
        presenza.nota_fornitore = p.get('nota_fornitore', '') or ''
        
        hostess_id = p.get('hostess_id')
        presenza.hostess = Hostess.objects.filter(pk=hostess_id).first() if hostess_id else None
        
        agenzia_id = p.get('agenzia_id')
        presenza.agenzia = Agenzia.objects.filter(pk=agenzia_id).first() if agenzia_id else None
        
        # Orari
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
    """Ricerca fornitore per autocomplete (HTMX)."""
    q = request.GET.get('q', '')
    
    if len(q) < 2:
        return render(request, 'pallet_promoter/partials/fornitore_results.html', {'results': []})
    
    fornitori = Fornitore.objects.filter(
        Q(nome__icontains=q) | Q(codice__icontains=q)
    )[:20]
    
    results = [
        {'id': f.codice, 'text': f"{f.codice} - {f.nome}"}
        for f in fornitori
    ]
    
    return render(request, 'pallet_promoter/partials/fornitore_results.html', {'results': results})

@csrf_exempt
@require_http_methods(["POST"])
def salva_fornitore_slot(request):
    """Salva fornitore per un singolo slot/giorno (griglia scelta fornitore)."""
    from datetime import datetime
    
    giorno_str = request.POST.get('giorno')
    slot = int(request.POST.get('slot'))
    fornitore_id = request.POST.get('fornitore_id')
    nota = request.POST.get('nota', '')
    
    giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()
    
    presenza, created = PresenzaHostess.objects.get_or_create(
        giorno=giorno,
        slot=slot,
        defaults={'tipo': 'STD'}
    )
    
    presenza.fornitore = Fornitore.objects.filter(pk=fornitore_id).first() if fornitore_id else None
    presenza.nota_fornitore = nota
    presenza.save()
    
    return JsonResponse({'success': True})