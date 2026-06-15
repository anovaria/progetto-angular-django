class PortalUserMiddleware:
    """Legge l'utente dalla sessione e lo mette su request.portal_user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            request.portal_user = request.session['user']
        except (KeyError, AttributeError, TypeError):
            request.portal_user = None
        return self.get_response(request)


class PortalAuthMiddleware:
    """Protegge tutte le route /app/ richiedendo una sessione portale attiva.
    Se la sessione manca o è stata invalidata (kick), redirige al login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    EXEMPT_PREFIXES = ['/app/cursori/']

    def __call__(self, request):
        exempt = any(request.path.startswith(p) for p in self.EXEMPT_PREFIXES)
        if not exempt and request.path.startswith('/app/') and not request.session.get('user'):
            from django.shortcuts import redirect
            return redirect('/portal/login/')
        return self.get_response(request)
