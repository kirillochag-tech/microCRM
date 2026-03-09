from django import template
from django.db.models import Q
from announcements.models import Announcement, AnnouncementReadStatus

register = template.Library()

@register.simple_tag(takes_context=True)
def get_user_announcements(context):
    """
    Template tag to get announcements for the current user.
    """
    request = context['request']
    user = request.user
    
    if not user.is_authenticated:
        return []
    
    # Get all possible announcements for the current user
    if user.role == 'MODERATOR':
        base_q = Q(target_audience='ALL_USERS') | Q(target_audience='ALL_EMPLOYEES') | Q(target_audience='MODERATORS')
    else:  # EMPLOYEE or CLIENT
        base_q = Q(target_audience='ALL_USERS') | Q(target_audience='ALL_EMPLOYEES')
    
    announcements = Announcement.objects.filter(
        base_q | Q(target_audience='CUSTOM', recipients=user)
    ).distinct().order_by('-created_at')
    
    # Prefetch read statuses for the current user
    from django.db import models
    announcements = announcements.prefetch_related(
        models.Prefetch(
            'read_statuses',
            queryset=AnnouncementReadStatus.objects.filter(user=user),
            to_attr='user_read_status'
        )
    )

    # Annotate with read status
    for announcement in announcements:
        read_status = getattr(announcement, 'user_read_status', [])
        if read_status:
            announcement.is_read = True
            announcement.is_acknowledged = read_status[0].acknowledged
        else:
            announcement.is_read = False
            announcement.is_acknowledged = False

    # Convert to list for sorting: unacknowledged first
    announcement_list = list(announcements)
    sorted_announcements = sorted(announcement_list, key=lambda x: (x.is_acknowledged, -x.created_at.timestamp()))
    
    return sorted_announcements