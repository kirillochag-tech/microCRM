from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import Announcement, AnnouncementReadStatus
from users.models import CustomUser


class AnnouncementReadView(LoginRequiredMixin, View):
    """View to handle announcement read status and acknowledgment."""
    
    def post(self, request, announcement_id):
        announcement = get_object_or_404(Announcement, id=announcement_id)
        user = request.user
        
        # Create or update read status
        read_status, created = AnnouncementReadStatus.objects.get_or_create(
            announcement=announcement,
            user=user,
            defaults={'acknowledged': False}
        )
        
        # If request has 'acknowledge' parameter, mark as acknowledged
        acknowledge = request.POST.get('acknowledge', False)
        if acknowledge:
            read_status.acknowledged = True
            read_status.save()
            messages.success(request, "Объявление подтверждено как прочитанное!")
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Объявление подтверждено как прочитанное'})
            else:
                # For non-AJAX requests, redirect back to referer or dashboard
                referer = request.META.get('HTTP_REFERER', '/')
                return redirect(referer)
        else:
            # Just mark as read (without acknowledgment)
            if created or not read_status.read_at:  # Only update if not previously read
                read_status.save()  # This will set read_at due to auto_now_add
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Объявление отмечено как прочитанное'})
            else:
                # For non-AJAX requests, redirect back to referer or dashboard
                referer = request.META.get('HTTP_REFERER', '/')
                return redirect(referer)


@login_required
def all_user_announcements(request):
    """Display all announcements for the current user."""
    user = request.user
    
    # Get all announcements for this user based on target audience
    announcements = Announcement.objects.filter(
        Q(target_audience='ALL_USERS') |
        Q(target_audience='ALL_EMPLOYEES') |
        Q(target_audience='MODERATORS') |  # Anyone can see moderator-targeted announcements if they are a moderator
        Q(target_audience='CUSTOM', recipients=user)
    ).distinct().order_by('-created_at')
    
    # Filter to only show announcements that should be visible to the current user
    filtered_announcements = []
    for announcement in announcements:
        if (announcement.target_audience == 'ALL_USERS' or
            announcement.target_audience == 'ALL_EMPLOYEES' or
            (announcement.target_audience == 'MODERATORS' and user.role == 'MODERATOR') or
            (announcement.target_audience == 'CUSTOM' and 
             announcement.recipients.filter(id=user.id).exists())):
            filtered_announcements.append(announcement)
    
    # Add read status information
    for announcement in filtered_announcements:
        try:
            read_status = AnnouncementReadStatus.objects.get(announcement=announcement, user=user)
            announcement.is_read = read_status.read_at is not None
            announcement.is_acknowledged = read_status.acknowledged
        except AnnouncementReadStatus.DoesNotExist:
            announcement.is_read = False
            announcement.is_acknowledged = False
    
    return render(request, 'announcements/all.html', {
        'announcements': filtered_announcements
    })


@login_required
def get_user_announcements(request):
    """Get announcements for the current user - returns all announcements with their read status, prioritizing unread/unacknowledged."""
    user = request.user
    
    # Get announcements based on target audience and user role
    announcements = Announcement.objects.filter(
        Q(target_audience='ALL_USERS') |
        Q(target_audience='ALL_EMPLOYEES') |
        Q(target_audience='MODERATORS') |  # Anyone can see moderator-targeted announcements if they are a moderator
        Q(target_audience='CUSTOM', recipients=user)
    ).distinct().order_by('-created_at')
    
    # Filter to only include announcements that should be visible to the current user
    filtered_announcements = []
    for announcement in announcements:
        if (announcement.target_audience == 'ALL_USERS' or
            announcement.target_audience == 'ALL_EMPLOYEES' or
            (announcement.target_audience == 'MODERATORS' and user.role == 'MODERATOR') or
            (announcement.target_audience == 'CUSTOM' and 
             announcement.recipients.filter(id=user.id).exists())):
            filtered_announcements.append(announcement)
    
    # Add read status information
    for announcement in filtered_announcements:
        try:
            read_status = AnnouncementReadStatus.objects.get(announcement=announcement, user=user)
            announcement.is_read = read_status.read_at is not None
            announcement.is_acknowledged = read_status.acknowledged
        except AnnouncementReadStatus.DoesNotExist:
            announcement.is_read = False
            announcement.is_acknowledged = False
    
    # Sort announcements: unacknowledged first, then by date
    sorted_announcements = sorted(filtered_announcements, key=lambda x: (x.is_acknowledged, -x.created_at.timestamp()))
    
    return sorted_announcements


@login_required
def get_unread_announcements(request):
    """Get only unread/unacknowledged announcements for the current user."""
    user = request.user
    
    # Get announcements that haven't been read or acknowledged
    announcements = Announcement.objects.filter(
        Q(target_audience='ALL_USERS') |
        Q(target_audience='ALL_EMPLOYEES') |
        Q(target_audience='MODERATORS') |  # Anyone can see moderator-targeted announcements if they are a moderator
        Q(target_audience='CUSTOM', recipients=user)
    ).distinct().order_by('-created_at')
    
    # Filter to only include announcements that should be visible to the current user
    filtered_announcements = []
    for announcement in announcements:
        if (announcement.target_audience == 'ALL_USERS' or
            announcement.target_audience == 'ALL_EMPLOYEES' or
            (announcement.target_audience == 'MODERATORS' and user.role == 'MODERATOR') or
            (announcement.target_audience == 'CUSTOM' and 
             announcement.recipients.filter(id=user.id).exists())):
            # Also check if it's not acknowledged yet
            try:
                read_status = AnnouncementReadStatus.objects.get(announcement=announcement, user=user)
                if not read_status.acknowledged:
                    filtered_announcements.append(announcement)
            except AnnouncementReadStatus.DoesNotExist:
                # If no read status exists, it hasn't been acknowledged
                filtered_announcements.append(announcement)
    
    # Add read status information
    for announcement in filtered_announcements:
        try:
            read_status = AnnouncementReadStatus.objects.get(announcement=announcement, user=user)
            announcement.is_read = read_status.read_at is not None
            announcement.is_acknowledged = read_status.acknowledged
        except AnnouncementReadStatus.DoesNotExist:
            announcement.is_read = False
            announcement.is_acknowledged = False
    
    return filtered_announcements


@login_required
def latest_announcement(request):
    """Get the latest announcement for display in the dashboard."""
    user = request.user
    
    # Get the latest announcement for this user
    announcements = Announcement.objects.filter(
        Q(target_audience='ALL_USERS') |
        Q(target_audience='ALL_EMPLOYEES') |
        Q(target_audience='MODERATORS') |  # Anyone can see moderator-targeted announcements if they are a moderator
        Q(target_audience='CUSTOM', recipients=user)
    ).distinct().order_by('-created_at')
    
    # Find the first announcement that is visible to the current user
    latest_announcement = None
    for announcement in announcements:
        if (announcement.target_audience == 'ALL_USERS' or
            announcement.target_audience == 'ALL_EMPLOYEES' or
            (announcement.target_audience == 'MODERATORS' and user.role == 'MODERATOR') or
            (announcement.target_audience == 'CUSTOM' and 
             announcement.recipients.filter(id=user.id).exists())):
            latest_announcement = announcement
            break  # Take the first one that matches the criteria
    
    if latest_announcement:
        try:
            read_status = AnnouncementReadStatus.objects.get(announcement=latest_announcement, user=user)
            latest_announcement.is_read = read_status.read_at is not None
            latest_announcement.is_acknowledged = read_status.acknowledged
        except AnnouncementReadStatus.DoesNotExist:
            latest_announcement.is_read = False
            latest_announcement.is_acknowledged = False
    else:
        latest_announcement = None
    
    return render(request, 'announcements/latest.html', {
        'announcement': latest_announcement
    })
