import os

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def rio_banner_info():
    """
    Info per il banner di rio_fornitori_new, da mostrare nel template.

    Ritorna:
      - dry_run: stato reale del trasferimento (== settings.RIO_DASH_DRY_RUN, la
        STESSA fonte usata da transfer.py); True = solo CSV, nessun invio a Gold.
      - env: ambiente (DJANGO_ENV, es. 'test' o 'prod') per l'etichetta.
    """
    return {
        'dry_run': getattr(settings, 'RIO_DASH_DRY_RUN', True),
        'env': os.environ.get('DJANGO_ENV', 'prod').strip().lower(),
    }
