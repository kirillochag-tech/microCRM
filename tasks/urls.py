from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # API endpoints that are used by admin
    path('api/grouped-answers/', views.getGroupedAnswers, name='grouped_answers_api'),
    path('api/mark-as-read/', views.markAsRead, name='mark_as_read_api'),
    path('api/autocomplete-clients/', views.autocomplete_clients, name='autocomplete_clients'),
    path('api/autocomplete-tasks/', views.autocomplete_tasks, name='autocomplete_tasks'),
]