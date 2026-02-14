# modules/auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .backends import LDAPBackend
from .models import UserAppPermission


class LoginLDAPAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        
        backend = LDAPBackend()
        try:
            user = backend.authenticate(request, username=username, password=password)
        except Exception as e:
            return Response({"detail": f"Errore LDAP: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if user:
            # Recupera le app autorizzate per questo utente
            user_apps = list(
                UserAppPermission.objects
                .filter(username=user.username.lower())
                .values_list('app_name', flat=True)
            )
            
            # Combina OU + Gruppi AD
            all_groups = list(set(
                getattr(user, 'ldap_ous', []) + 
                getattr(user, 'ldap_groups', [])
            ))
            
            return Response({
                "username": user.username,
                "apps": user_apps,
                "groups": all_groups,  # OU + Gruppi AD
                "ous": getattr(user, 'ldap_ous', []),
                "ad_groups": getattr(user, 'ldap_groups', []),
            }, status=status.HTTP_200_OK)
        
        return Response({"detail": "Credenziali non valide"}, status=status.HTTP_401_UNAUTHORIZED)