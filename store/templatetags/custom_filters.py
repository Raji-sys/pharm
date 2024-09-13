from django import template

register = template.Library()

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)