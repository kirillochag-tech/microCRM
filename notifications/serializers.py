from rest_framework import serializers
from .models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationSerializer(serializers.ModelSerializer):
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_username', 'notification_type', 
            'title', 'message', 'task', 'task_title', 'is_read', 
            'created_at', 'read_at'
        ]
        read_only_fields = ['created_at', 'read_at']