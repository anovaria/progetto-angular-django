from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from modules.util.test_db import test_goldreport_connection
from modules.auth.backends import LDAPBackend
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes # <-- AGGIUNGI parser_classes QUI
from rest_framework.parsers import JSONParser, FormParser
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt # AGGIUNGI QUESTO!
@api_view(['POST'])
@parser_classes([JSONParser, FormParser]) # <--- AGGIUNGI QUESTO
@permission_classes([])             # Route pubblica
@authentication_classes([])                 # Nessuna auth DRF
def ldap_login_test(request):
    username = request.data.get('username')
    password = request.data.get('password')

    backend = LDAPBackend()
    user = backend.authenticate(request, username=username, password=password)

    if user:
        return Response({
            "username": user.username,
            "groups": getattr(user, "ldap_ous", [])
        }, status=status.HTTP_200_OK)

    return Response(
        {"detail": "Credenziali non valide"},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def db_test(request):
    try:
        rows = test_goldreport_connection()
        return Response({"success": True, "data": rows})
    except Exception as e:
        return Response({"success": False, "error": str(e)})
