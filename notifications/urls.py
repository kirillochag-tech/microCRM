from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('count/', views.get_notifications_count, name='notifications_count'),
]