from .views import get_visible_menu
from modules.auth.models import UserAppPermission

def portal_menu(request):
    """Inietta menu e utente sessione in tutti i template."""
    user = getattr(request, 'portal_user', None)
    if not user:
        return {}

    username = user.get('username', '')
    user_app_permissions = list(
        UserAppPermission.objects
        .filter(username=username.lower())
        .values_list('app_name', flat=True)
    )

    menu = get_visible_menu(user.get('groups', []), username, user_app_permissions)
    current = request.path

    for item in menu:
        item['parent_active'] = current.startswith(item['path']) if item['path'] != '/' else current == '/'
        for child in item.get('children', []):
            child['child_active'] = current == child['path']

    return {'portal_user': user, 'menu': menu, 'current_path': current}