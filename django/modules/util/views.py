# Modulo di utilità generale del portale
"""
Util - Views
Modulo di utilità generale del portale: login LDAP, test connessione DB e messaggi di sistema.

Funzionalità:
- ldap_login_test: endpoint POST pubblico per verificare le credenziali LDAP
- db_test: endpoint GET per testare la connessione al database 'goldreport'
- check_message: endpoint GET che restituisce il messaggio urgente di sistema, se presente,
  filtrandolo per destinatari specifici se la lista non è vuota
"""
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from modules.util.test_db import test_goldreport_connection
from modules.auth.backends import LDAPBackend
# parser_classes consente di accettare sia JSON che form-encoded nella stessa view DRF
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.parsers import JSONParser, FormParser
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.http import JsonResponse


@csrf_exempt          # Necessario perché la richiesta viene da client non-browser senza cookie CSRF
@api_view(['POST'])
@parser_classes([JSONParser, FormParser])   # Accetta sia body JSON che form-encoded
@permission_classes([])                     # Rotta pubblica: nessun permesso DRF richiesto
@authentication_classes([])                 # Nessuna autenticazione DRF (login avviene qui)
def ldap_login_test(request):
    """Verifica le credenziali utente tramite LDAP.

    Riceve username e password nel body della richiesta (JSON o form-encoded),
    tenta l'autenticazione tramite LDAPBackend e restituisce i dati dell'utente
    (username e gruppi/OU) se le credenziali sono valide.

    Body params:
        username (str): nome utente di dominio
        password (str): password in chiaro

    Risposta 200: { username: str, groups: list }
    Risposta 401: { detail: "Credenziali non valide" }
    """
    username = request.data.get('username')
    password = request.data.get('password')

    # Usa il backend LDAP personalizzato per autenticare contro Active Directory
    backend = LDAPBackend()
    user = backend.authenticate(request, username=username, password=password)

    if user:
        return Response({
            "username": user.username,
            # ldap_ous contiene le unità organizzative LDAP dell'utente (gruppi)
            "groups": getattr(user, "ldap_ous", [])
        }, status=status.HTTP_200_OK)

    return Response(
        {"detail": "Credenziali non valide"},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def db_test(request):
    """Verifica la connessione al database 'goldreport'.

    Chiama test_goldreport_connection() che esegue una query diagnostica
    e restituisce le prime righe. Utile per verificare che la connessione
    al DB sia attiva e funzionante.

    Risposta 200: { success: true, data: [...] }
    Risposta 200: { success: false, error: str } (in caso di eccezione)
    """
    try:
        rows = test_goldreport_connection()
        return Response({"success": True, "data": rows})
    except Exception as e:
        return Response({"success": False, "error": str(e)})


def check_message(request):
    """Restituisce il messaggio urgente di sistema dalla cache, se presente e applicabile.

    Il messaggio è memorizzato in cache con la chiave 'sitemsg_urgente' ed è un dict
    con almeno il campo 'destinatari' (lista di username) e il contenuto del messaggio.

    Logica di filtraggio:
    1. Se l'utente non è autenticato (portal_user assente), non mostra nessun messaggio.
    2. Se la cache non contiene 'sitemsg_urgente', non mostra nessun messaggio.
    3. Se 'destinatari' è una lista vuota, il messaggio è per tutti gli utenti.
    4. Se 'destinatari' è valorizzata, il messaggio è mostrato solo agli username in lista.

    Risposta JSON: { message: dict } oppure { message: null }
    """
    # Se l'utente non è autenticato tramite il middleware portal_user, non mostrare nulla
    if not request.portal_user:
        return JsonResponse({'message': None})

    username = request.portal_user.get('username')
    # Legge il messaggio urgente dalla cache (None se scaduto o non impostato)
    msg = cache.get('sitemsg_urgente')

    if msg is None:
        return JsonResponse({'message': None})

    # Se destinatari è valorizzata, mostra il messaggio solo agli username presenti nella lista
    destinatari = msg.get('destinatari', [])
    if destinatari and username not in destinatari:
        return JsonResponse({'message': None})

    return JsonResponse({'message': msg})
