from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from tasks.models import Task, SurveyAnswer, PhotoReport
from tasks.serializers import TaskSerializer, SurveyAnswerSerializer, PhotoReportSerializer

class TaskListView(generics.ListCreateAPIView):
    """
    Получение списка задач или создание новой задачи
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Модераторы видят все задачи, сотрудники - только назначенные им
        user = self.request.user
        if user.role == 'MODERATOR':
            return Task.objects.all()
        elif user.role == 'EMPLOYEE':
            return Task.objects.filter(assigned_to=user)
        else:
            return Task.objects.none()


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Получение, обновление или удаление конкретной задачи
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'MODERATOR':
            return Task.objects.all()
        elif user.role == 'EMPLOYEE':
            return Task.objects.filter(assigned_to=user)
        else:
            return Task.objects.none()


class SurveyAnswerListView(generics.ListCreateAPIView):
    """
    Получение списка ответов на анкеты или создание нового ответа
    """
    queryset = SurveyAnswer.objects.all()
    serializer_class = SurveyAnswerSerializer
    permission_classes = [permissions.IsAuthenticated]


class SurveyAnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Получение, обновление или удаление конкретного ответа на анкету
    """
    queryset = SurveyAnswer.objects.all()
    serializer_class = SurveyAnswerSerializer
    permission_classes = [permissions.IsAuthenticated]


class PhotoReportListView(generics.ListCreateAPIView):
    """
    Получение списка фотоотчетов или создание нового фотоотчета
    """
    queryset = PhotoReport.objects.all()
    serializer_class = PhotoReportSerializer
    permission_classes = [permissions.IsAuthenticated]


class PhotoReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Получение, обновление или удаление конкретного фотоотчета
    """
    queryset = PhotoReport.objects.all()
    serializer_class = PhotoReportSerializer
    permission_classes = [permissions.IsAuthenticated]