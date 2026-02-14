"""
Active Users - Middleware
Traccia automaticamente ogni richiesta autenticata.
Da aggiungere in modules/active_users/middleware.py
"""
import logging
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger(__name__)

# Soglia minima tra aggiornamenti per lo stesso utente (in secondi).
# Evita scritture su DB ad ogni singola richiesta (es. ogni asset statico).
UPDATE_THRESHOLD_SECONDS = 30

# Cache in memoria per evitare query continue
_last_update_cache = {}


class ActiveUserMiddleware:
    """
    Middleware che registra l'attività dell'utente autenticato.
    
    Aggiunge/aggiorna un record UserActivity per ogni utente autenticato,
    con throttling per evitare troppe scritture su DB.
    
    Aggiungere in settings/base.py MIDDLEWARE:
        'modules.active_users.middleware.ActiveUserMiddleware',
    
    NOTA: Deve stare DOPO 'django.contrib.auth.middleware.AuthenticationMiddleware'
    o dopo il tuo middleware di autenticazione LDAP.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Traccia solo utenti autenticati
        if not self._is_authenticated(request):
            return response

        # Ignora richieste a risorse statiche e admin
        path = request.path
        if self._should_skip(path):
            return response

        username = self._get_username(request)
        if not username:
            return response

        # Throttle: aggiorna solo se è passato abbastanza tempo
        now = timezone.now()
        last = _last_update_cache.get(username)
        if last and (now - last).total_seconds() < UPDATE_THRESHOLD_SECONDS:
            return response

        # Aggiorna la cache in memoria
        _last_update_cache[username] = now

        # Aggiorna il DB (update_or_create)
        try:
            from .models import UserActivity

            env = getattr(settings, 'PORTAL_ENVIRONMENT', 'dev')
            display_name = self._get_display_name(request)
            ip = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

            UserActivity.objects.update_or_create(
                username=username,
                environment=env,
                defaults={
                    'display_name': display_name,
                    'last_path': path[:500],
                    'ip_address': ip,
                    'user_agent': user_agent,
                }
            )
        except Exception as e:
            logger.warning(f"ActiveUserMiddleware: errore aggiornamento per {username}: {e}")

        return response

    def _is_authenticated(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return True
        if request.META.get('REMOTE_USER'):
            return True
        if request.META.get('HTTP_X_AUTH_USER'):
            return True
        if request.GET.get('_auth_user'):
            return True
        return False

    def _get_username(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user.username.lower()
        remote = request.META.get('REMOTE_USER', '')
        if remote:
            if '\\' in remote:
                remote = remote.split('\\')[-1]
            return remote.lower()
        auth_user = request.META.get('HTTP_X_AUTH_USER', '')
        if auth_user:
            return auth_user.lower()
        param_user = request.GET.get('_auth_user', '')
        if param_user:
            return param_user.lower()
        return None

    def _get_display_name(self, request):
        """Recupera il nome visualizzato se disponibile."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            full = request.user.get_full_name()
            if full:
                return full
            return request.user.username
        return self._get_username(request) or ''

    def _get_client_ip(self, request):
        """Recupera l'IP del client, gestendo proxy/load balancer."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _should_skip(self, path):
        """Ignora percorsi che non rappresentano navigazione utente reale."""
        skip_prefixes = (
            '/static/',
            '/media/',
            '/favicon.ico',
            '/__debug__/',
            '/admin/jsi18n/',
        )
        return path.startswith(skip_prefixes)
