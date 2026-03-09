from rest_framework import serializers
from .models import Task, SurveyAnswer, PhotoReport, PhotoReportItem
from users.models import CustomUser
from clients.models import Client

class TaskSerializer(serializers.ModelSerializer):
    assigned_to_username = serializers.CharField(source='assigned_to.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class SurveyAnswerSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = SurveyAnswer
        fields = '__all__'
        read_only_fields = ('created_at',)


class PhotoReportSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = PhotoReport
        fields = '__all__'
        read_only_fields = ('created_at',)


class PhotoReportItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoReportItem
        fields = '__all__'
        read_only_fields = ('created_at',)