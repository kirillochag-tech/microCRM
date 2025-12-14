# tasks/urls.py
from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('list/', views.TaskListView.as_view(), name='task_list'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('survey/<int:task_id>/', views.SurveyResponseView.as_view(), name='survey_response'),
    path('survey/<int:task_id>/results/', views.SurveyResultsView.as_view(), name='survey_results'),
    path('answer/<int:answer_id>/add-photos/', views.AddPhotosView.as_view(), name='add_photos'),  
    path('answer/<int:answer_id>/add-single-photo/', views.AddSinglePhotoView.as_view(), name='add_single_photo'),
    path('my-surveys/', views.MySurveysView.as_view(), name='my_surveys'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    path('search_clients/', views.search_clients, name='search_clients'),
    path('autocomplete_clients/', views.autocomplete_clients, name='autocomplete_clients'),

]