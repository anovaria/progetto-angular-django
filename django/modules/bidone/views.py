from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import BidoneAnnotazione


@require_POST
def annota(request):
    app_name   = request.POST.get('app_name', '').strip()
    record_key = request.POST.get('record_key', '').strip()
    if not app_name or not record_key:
        return JsonResponse({'ok': False, 'error': 'parametri mancanti'}, status=400)

    gestito = request.POST.get('gestito') == '1'
    nota    = request.POST.get('nota', '').strip()
    utente = (
        (getattr(request, 'portal_user', None) or {}).get('username')
        or getattr(request.user, 'username', None)
        or 'anonimo'
    )

    BidoneAnnotazione.objects.update_or_create(
        app_name=app_name,
        record_key=record_key,
        defaults={'gestito': gestito, 'nota': nota, 'utente': utente},
    )
    return JsonResponse({'ok': True})


def carica_annotazioni(app_name: str) -> dict:
    """
    Ritorna {record_key: dict} per tutte le annotazioni di un'app.
    Da chiamare nelle view dei moduli Bidone per sovrapporre alle righe Gold.
    """
    return {
        a.record_key: {
            'gestito':       a.gestito,
            'nota':          a.nota,
            'utente':        a.utente,
            'aggiornato_il': a.aggiornato_il,
        }
        for a in BidoneAnnotazione.objects.filter(app_name=app_name)
    }
