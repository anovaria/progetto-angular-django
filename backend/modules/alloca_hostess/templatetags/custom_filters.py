from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Accede a un dizionario con chiave numerica."""
    if dictionary is None:
        return None
    return dictionary.get(key)