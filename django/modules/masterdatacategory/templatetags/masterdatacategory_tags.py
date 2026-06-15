from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    request = context['request']
    updated = request.GET.copy()
    for k, v in kwargs.items():
        updated[k] = v
    return updated.urlencode()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
