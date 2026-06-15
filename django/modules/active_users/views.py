"""
Active Users - Views
API e pagina per consultare gli utenti attivi.
"""
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_GET
from datetime import timedelta
from .models import UserActivity

# ============================================================
# Modulo: active_users/views.py
# Fornisce la pagina dashboard e due API JSON per monitorare
# gli utenti connessi al portale in tempo reale.
# - active_users_api: utenti attivi negli ultimi N minuti
# - active_users_history_api: storico attività nelle ultime N ore
# ============================================================


def _get_current_env():
    """Restituisce l'ambiente corrente del portale (es. 'dev', 'prod').
    Legge la variabile PORTAL_ENVIRONMENT dalle impostazioni Django;
    se assente, restituisce 'dev' come valore di default."""
    return getattr(settings, 'PORTAL_ENVIRONMENT', 'dev')


def active_users_page(request):
    """Vista della pagina dashboard degli utenti online.
    Richiede che l'utente sia autenticato tramite sessione;
    in caso contrario reindirizza al login."""
    if not request.session.get('user'):
        return redirect('/portal/login/')
    return render(request, 'active_users/dashboard.html')


@require_GET
def active_users_api(request):
    """
    Restituisce la lista degli utenti attivi negli ultimi N minuti.

    Query params:
        minutes: int (default 5) - finestra temporale in minuti
        env: str (default: ambiente corrente) - filtra per ambiente (all = tutti)

    Risposta JSON:
        count           - numero di utenti attivi
        threshold_minutes - finestra usata per il filtro
        current_environment - ambiente del server
        filter_environment  - ambiente applicato al filtro
        server_time     - timestamp corrente ISO 8601
        users           - lista di dizionari con dati utente
    """
    # Legge e valida il parametro 'minutes' (min 1, max 60)
    try:
        minutes = int(request.GET.get('minutes', 5))
        minutes = max(1, min(minutes, 60))
    except (ValueError, TypeError):
        minutes = 5

    # Determina il filtro ambiente (default: ambiente attuale del server)
    env_filter = request.GET.get('env', _get_current_env())

    now = timezone.now()
    # Calcola la soglia temporale: considera attivi solo i record successivi a questo istante
    threshold = now - timedelta(minutes=minutes)

    # Filtra i record di attività più recenti della soglia
    qs = UserActivity.objects.filter(last_activity__gte=threshold)

    # Applica il filtro per ambiente se non è 'all'
    if env_filter != 'all':
        qs = qs.filter(environment=env_filter)

    # Ordina per ultima attività decrescente (più recenti prima)
    active = qs.order_by('-last_activity')

    users_data = []
    for ua in active:
        # Calcola i secondi di inattività dall'ultima azione registrata
        idle = (now - ua.last_activity).total_seconds()
        users_data.append({
            'username': ua.username,
            'display_name': ua.display_name,
            'last_activity': ua.last_activity.isoformat(),
            'last_path': ua.last_path,
            'ip_address': ua.ip_address,
            'idle_seconds': round(idle),
            'environment': ua.environment,
        })

    return JsonResponse({
        'count': len(users_data),
        'threshold_minutes': minutes,
        'current_environment': _get_current_env(),
        'filter_environment': env_filter,
        'server_time': now.isoformat(),
        'users': users_data,
    })


@require_GET
def active_users_history_api(request):
    """
    Restituisce TUTTI i record (anche offline) per lo storico.

    Query params:
        hours: int (default 24) - finestra temporale in ore
        env: str (default: ambiente corrente) - filtra per ambiente (all = tutti)

    Risposta JSON identica a active_users_api, con in più il campo
    'is_online' (True se l'utente è risultato attivo negli ultimi 5 minuti).
    """
    # Legge e valida il parametro 'hours' (min 1, max 168 = 7 giorni)
    try:
        hours = int(request.GET.get('hours', 24))
        hours = max(1, min(hours, 168))
    except (ValueError, TypeError):
        hours = 24

    env_filter = request.GET.get('env', _get_current_env())

    now = timezone.now()
    threshold = now - timedelta(hours=hours)

    qs = UserActivity.objects.filter(last_activity__gte=threshold)

    if env_filter != 'all':
        qs = qs.filter(environment=env_filter)

    all_users = qs.order_by('-last_activity')

    users_data = []
    for ua in all_users:
        idle = (now - ua.last_activity).total_seconds()
        users_data.append({
            'username': ua.username,
            'display_name': ua.display_name,
            'last_activity': ua.last_activity.isoformat(),
            'last_path': ua.last_path,
            'ip_address': ua.ip_address,
            'idle_seconds': round(idle),
            # Considera l'utente "online" se ha agito negli ultimi 5 minuti (300 secondi)
            'is_online': idle < 300,
            'environment': ua.environment,
        })

    return JsonResponse({
        'count': len(users_data),
        'threshold_hours': hours,
        'current_environment': _get_current_env(),
        'filter_environment': env_filter,
        'server_time': now.isoformat(),
        'users': users_data,
    })


@require_GET
def debug_auth(request):
    """Endpoint di debug: restituisce le informazioni sull'IP del client
    e gli header HTTP_X_* presenti nella richiesta. Utile per diagnosticare
    proxy e configurazioni di reverse-proxy."""
    return JsonResponse({
        'remote_addr': request.META.get('REMOTE_ADDR'),
        'x_forwarded_for': request.META.get('HTTP_X_FORWARDED_FOR'),
        'x_real_ip': request.META.get('HTTP_X_REAL_IP'),
        # Raccoglie tutti gli header custom con prefisso X- (es. X-Auth-User)
        'all_x_headers': {k: v for k, v in request.META.items() if k.startswith('HTTP_X')},
    })
