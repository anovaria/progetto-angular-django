"""
Active Users - Views
API per consultare gli utenti attivi.
Da aggiungere in modules/active_users/views.py
"""
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_GET
from datetime import timedelta
from .models import UserActivity


def _get_current_env():
    return getattr(settings, 'PORTAL_ENVIRONMENT', 'dev')


@require_GET
def active_users_api(request):
    """
    Restituisce la lista degli utenti attivi negli ultimi N minuti.
    
    Query params:
        minutes: int (default 5) - finestra temporale in minuti
        env: str (default: ambiente corrente) - filtra per ambiente (all = tutti)
    """
    try:
        minutes = int(request.GET.get('minutes', 5))
        minutes = max(1, min(minutes, 60))
    except (ValueError, TypeError):
        minutes = 5

    env_filter = request.GET.get('env', _get_current_env())

    now = timezone.now()
    threshold = now - timedelta(minutes=minutes)

    qs = UserActivity.objects.filter(last_activity__gte=threshold)

    if env_filter != 'all':
        qs = qs.filter(environment=env_filter)

    active = qs.order_by('-last_activity')

    users_data = []
    for ua in active:
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
    """
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
    return JsonResponse({
        'remote_addr': request.META.get('REMOTE_ADDR'),
        'x_forwarded_for': request.META.get('HTTP_X_FORWARDED_FOR'),
        'x_real_ip': request.META.get('HTTP_X_REAL_IP'),
        'all_x_headers': {k: v for k, v in request.META.items() if k.startswith('HTTP_X')},
    })
