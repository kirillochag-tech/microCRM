from django.urls import path
from . import api_views

app_name = 'tasks_api'

urlpatterns = [
    # API endpoints for tasks
    path('tasks/', api_views.TaskListView.as_view(), name='task-list'),
    path('tasks/<int:pk>/', api_views.TaskDetailView.as_view(), name='task-detail'),
    
    # API endpoints for survey answers
    path('survey-answers/', api_views.SurveyAnswerListView.as_view(), name='survey-answer-list'),
    path('survey-answers/<int:pk>/', api_views.SurveyAnswerDetailView.as_view(), name='survey-answer-detail'),
    
    # API endpoints for photo reports
    path('photo-reports/', api_views.PhotoReportListView.as_view(), name='photo-report-list'),
    path('photo-reports/<int:pk>/', api_views.PhotoReportDetailView.as_view(), name='photo-report-detail'),
]