import os
from django.core.wsgi import get_wsgi_application

DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev").lower()  # default dev
# mappa i nomi corretti
env_map = {
    "dev": "project_core.settings.dev",
    "development": "project_core.settings.dev",
    "prod": "project_core.settings.prod",
    "production": "project_core.settings.prod"
}
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    env_map.get(DJANGO_ENV, "project_core.settings.dev")
)
application = get_wsgi_application()
