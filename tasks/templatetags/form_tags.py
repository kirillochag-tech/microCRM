# tasks/templatetags/form_tags.py

from django import template
import math

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Получает элемент из словаря по ключу.
    Используется в шаблонах для доступа к полям формы по ключу вопроса.
    """
    return dictionary.get(f'question_{key}')

@register.filter
def multiply(value, arg):
    """Умножает значение на аргумент."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def round_half_up(value):
    """Округляет значение до 0.5 (например, 12.3 -> 12.5, 12.6 -> 13.0)"""
    try:
        num = float(value)
        return round(num * 2) / 2.0
    except (ValueError, TypeError):
        return 0

@register.filter
def round_to_half_percent(value):
    """Округляет процент до 0.5%"""
    try:
        num = float(value)
        rounded = round(num * 2) / 2.0
        return f"{rounded:.1f}"
    except (ValueError, TypeError):
        return "0.0"