from django.urls import path
from . import views

app_name = 'announcements'

urlpatterns = [
    path('read/<int:announcement_id>/', views.AnnouncementReadView.as_view(), name='mark_read'),
    path('latest/', views.latest_announcement, name='latest'),
    path('all/', views.all_user_announcements, name='all'),
]