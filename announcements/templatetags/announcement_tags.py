from django import template
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from announcements.views import get_user_announcements

register = template.Library()

@register.simple_tag(takes_context=True)
def get_user_announcements(context):
    """
    Template tag to get announcements for the current user.
    """
    request = context['request']
    return get_user_announcements(request)