from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Accede a un dizionario con chiave dinamica nel template."""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def add_days(value, days):
    """Aggiunge giorni a una data."""
    try:
        return value + timedelta(days=int(days))
    except:
        return value
