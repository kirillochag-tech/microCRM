from django.urls import path
from . import api_views

app_name = 'notifications_api'

urlpatterns = [
    # API endpoints
    path('notifications/', api_views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', api_views.NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/<int:pk>/read/', api_views.mark_notification_as_read, name='notification-mark-read'),
    path('notifications/mark-all-read/', api_views.mark_all_notifications_as_read, name='notifications-mark-all-read'),
    path('notifications/unread-count/', api_views.get_unread_notifications_count, name='notifications-unread-count'),
]