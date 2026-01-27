#views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .backends import LDAPBackend

class LoginLDAPAPIView(APIView):
    permission_classes = []  # nessuna auth per il login

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        backend = LDAPBackend()
        user = backend.authenticate(request, username=username, password=password)
        if user:
            return Response({
                "username": user.username,
                "groups": getattr(user, 'ldap_ous', [])
            }, status=status.HTTP_200_OK)
        return Response({"detail": "Credenziali non valide"}, status=status.HTTP_401_UNAUTHORIZED)
