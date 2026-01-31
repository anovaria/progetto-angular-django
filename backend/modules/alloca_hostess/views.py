from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from modules.pallet_promoter.models import Agenzia, Fornitore, Hostess, Periodo, PresenzaHostess
from django.views.decorators.csrf import csrf_exempt


def get_current_user(request):
    """Ottiene l'utente corrente dall'header LDAP o dalla sessione."""
    return request.META.get('HTTP_X_REMOTE_USER', request.user.username if request.user.is_authenticated else 'anonymous')


def index(request):
    """Dashboard Alloca Hostess."""
    oggi = timezone.now().date()
    
    # Periodo corrente
    periodo_corrente = Periodo.objects.filter(
        data_inizio__lte=oggi,
        data_fine__gte=oggi
    ).first()
    
    # Statistiche
    hostess_attive = Hostess.objects.filter(attiva=True).count()
    agenzie_count = Agenzia.objects.count()
    
    # Presenze oggi
    presenze_oggi = PresenzaHostess.objects.filter(giorno=oggi).count()
    
    context = {
        'periodo_corrente': periodo_corrente,
        'hostess_attive': hostess_attive,
        'agenzie_count': agenzie_count,
        'presenze_oggi': presenze_oggi,
        'oggi': oggi,
        'current_user': get_current_user(request),
    }
    return render(request, 'alloca_hostess/index.html', context)


def hostess_list(request):
    """Elenco Hostess."""
    hostess = Hostess.objects.all().order_by('nominativo')
    
    # Filtro attive
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

@csrf_exempt
def individuazione(request):
    """Individuazione/Coordinamento Hostess - Form principale."""
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
        return render(request, 'alloca_hostess/no_periodo.html')
    
    # Giorno selezionato
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
    
    # Limita al periodo
    if giorno < periodo.data_inizio:
        giorno = periodo.data_inizio
    elif giorno > periodo.data_fine:
        giorno = periodo.data_fine
    
    # Navigazione
    giorno_prec = giorno - timedelta(days=1) if giorno > periodo.data_inizio else None
    giorno_succ = giorno + timedelta(days=1) if giorno < periodo.data_fine else None
    
    # Slot attivi
    num_slots = min(periodo.num_hostess or 12, 13)
    
    # Presenze del giorno
    presenze = {}
    for slot in range(1, num_slots + 1):
        presenza = PresenzaHostess.objects.filter(giorno=giorno, slot=slot).first()
        if not presenza:
            presenza = PresenzaHostess(giorno=giorno, slot=slot)
        presenze[slot] = presenza
    
    # Lista giorni per storico
    giorni_periodo = []
    current = periodo.data_inizio
    while current <= periodo.data_fine:
        presenze_giorno = PresenzaHostess.objects.filter(giorno=current).select_related('hostess', 'fornitore', 'agenzia')
        giorni_periodo.append({
            'data': current,
            'presenze': list(presenze_giorno),
        })
        current += timedelta(days=1)
    
    # Liste dropdown
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
    return render(request, 'alloca_hostess/individuazione.html', context)

@csrf_exempt
@require_http_methods(["GET"])
def cerca_fornitore(request):
    """API ricerca fornitore."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return render(request, 'alloca_hostess/partials/fornitore_results.html', {'fornitori': []})
    
    fornitori = Fornitore.objects.filter(nome__icontains=q)[:15]
    return render(request, 'alloca_hostess/partials/fornitore_results.html', {'fornitori': fornitori})


@require_http_methods(["POST"])
def salva_presenze(request):
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
def orari_hostess(request):
    """Registrazione orari giornalieri hostess - Vista semplificata."""
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
    
    # Trova tutte le presenze hostess per questa data (slot 1-12)
    presenze_hostess = []
    for slot_num in range(1, 13):  # 12 slot
        presenza = PresenzaHostess.objects.filter(giorno=data, slot=slot_num).select_related('hostess', 'agenzia').first()
        if not presenza:
            # Crea oggetto vuoto (non salvato)
            presenza = PresenzaHostess(giorno=data, slot=slot_num)
        
        presenze_hostess.append({
            'slot': slot_num,
            'presenza': presenza,
        })
    
    context = {
        'data': data,
        'data_prec': data_prec,
        'data_succ': data_succ,
        'presenze_hostess': presenze_hostess,
        'current_user': get_current_user(request),
    }
    return render(request, 'alloca_hostess/orari_hostess.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def salva_orario_hostess(request):
    """Salva orari hostess per uno slot in un giorno."""
    giorno_str = request.POST.get('giorno')
    slot = request.POST.get('slot')
    
    try:
        giorno = datetime.strptime(giorno_str, '%Y-%m-%d').date()
    except:
        return JsonResponse({'success': False, 'error': 'Data non valida'})
    
    # Prendi o crea presenza
    presenza, created = PresenzaHostess.objects.get_or_create(
        giorno=giorno,
        slot=slot
    )
    
    # Aggiorna orari
    ingresso_m = request.POST.get('ingresso_mattino')
    uscita_m = request.POST.get('uscita_mattino')
    ingresso_p = request.POST.get('ingresso_pomeriggio')
    uscita_p = request.POST.get('uscita_pomeriggio')
    
    presenza.ingresso_mattino = ingresso_m if ingresso_m else None
    presenza.uscita_mattino = uscita_m if uscita_m else None
    presenza.ingresso_pomeriggio = ingresso_p if ingresso_p else None
    presenza.uscita_pomeriggio = uscita_p if uscita_p else None
    
    presenza.save()
    
    # Calcola ore lavorate (opzionale, se vuoi mostrarle)
    ore_lavorate = 0
    if presenza.ingresso_mattino and presenza.uscita_mattino:
        delta_m = datetime.combine(giorno, presenza.uscita_mattino) - datetime.combine(giorno, presenza.ingresso_mattino)
        ore_lavorate += delta_m.total_seconds() / 3600
    
    if presenza.ingresso_pomeriggio and presenza.uscita_pomeriggio:
        delta_p = datetime.combine(giorno, presenza.uscita_pomeriggio) - datetime.combine(giorno, presenza.ingresso_pomeriggio)
        ore_lavorate += delta_p.total_seconds() / 3600
    
    return JsonResponse({
        'success': True,
        'ore_lavorate': round(ore_lavorate, 2)
    })
