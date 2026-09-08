from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Accesso a dizionario per chiave nel template: {{ dict|get_item:key }}"""
    return dictionary.get(key, '')
