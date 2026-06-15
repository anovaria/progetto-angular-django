# modules/auth/views.py
"""
Modulo views del modulo di autenticazione.

Espone un'API REST (Django REST Framework) per il login tramite LDAP.
Restituisce le informazioni sull'utente autenticato: username, app autorizzate,
gruppi LDAP (OU + gruppi AD) separati per comodità del frontend Angular.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .backends import LDAPBackend
from .models import UserAppPermission


class LoginLDAPAPIView(APIView):
    """
    Endpoint API per l'autenticazione LDAP degli utenti del portale.

    Accetta richieste POST con 'username' e 'password' nel corpo JSON.
    Non richiede autenticazione preesistente (AllowAny), poiché è il punto
    di ingresso per l'ottenimento delle credenziali di sessione.

    Risposta in caso di successo (HTTP 200):
    - username: nome utente autenticato
    - apps: lista delle app con permesso individuale nel database
    - groups: unione di OU e gruppi AD (usata dal frontend per il menu)
    - ous: solo le Organizational Unit LDAP
    - ad_groups: solo i gruppi Active Directory

    Risposta in caso di errore:
    - HTTP 401 se le credenziali sono errate
    - HTTP 500 se si verifica un errore di connessione LDAP
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Autentica l'utente tramite LDAP e restituisce i dati di sessione."""
        username = request.data.get("username")
        password = request.data.get("password")

        backend = LDAPBackend()
        try:
            user = backend.authenticate(request, username=username, password=password)
        except Exception as e:
            # Errore di connessione o configurazione LDAP: restituisce 500
            return Response({"detail": f"Errore LDAP: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if user:
            # Recupera le app autorizzate per questo utente tramite permessi individuali
            user_apps = list(
                UserAppPermission.objects
                .filter(username=user.username.lower())
                .values_list('app_name', flat=True)
            )

            # Combina OU + Gruppi AD in un'unica lista senza duplicati
            all_groups = list(set(
                getattr(user, 'ldap_ous', []) +
                getattr(user, 'ldap_groups', [])
            ))

            return Response({
                "username": user.username,
                "apps": user_apps,
                "groups": all_groups,  # OU + Gruppi AD (usato per il filtraggio del menu)
                "ous": getattr(user, 'ldap_ous', []),
                "ad_groups": getattr(user, 'ldap_groups', []),
            }, status=status.HTTP_200_OK)

        # Credenziali non valide: risposta 401 senza dettagli tecnici
        return Response({"detail": "Credenziali non valide"}, status=status.HTTP_401_UNAUTHORIZED)
