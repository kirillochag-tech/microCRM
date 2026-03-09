# tasks/urls.py
from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('list/', views.TaskListView.as_view(), name='task_list'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('survey/<int:task_id>/', views.SurveyResponseView.as_view(), name='survey_response'),
    path('photo/<int:task_id>/', views.PhotoReportView.as_view(), name='photo_report'),
    path('survey/<int:task_id>/results/', views.SurveyResultsView.as_view(), name='survey_results'),
    path('answer/<int:answer_id>/add-photos/', views.AddPhotosView.as_view(), name='add_photos'),  
    path('answer/<int:answer_id>/add-single-photo/', views.AddSinglePhotoView.as_view(), name='add_single_photo'),
    path('my-surveys/', views.MySurveysView.as_view(), name='my_surveys'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    path('search_clients/', views.search_clients, name='search_clients'),
    path('autocomplete_clients/', views.autocomplete_clients, name='autocomplete_clients'),
    path('autocomplete_tasks/', views.autocomplete_tasks, name='autocomplete_tasks'),
    path('api/process-equipment-photo-report/', views.process_equipment_photo_report, name='process_equipment_photo_report'),
    path('api/accept-equipment-photo-report/', views.accept_equipment_photo_report, name='accept_equipment_photo_report'),
    path('api/send-photo-report-to-rework/', views.send_photo_report_to_rework, name='send_photo_report_to_rework'),
    path('api/save-personal-comment/', views.save_personal_comment, name='save_personal_comment'),
    path('api/equipment-photo-reports/', views.equipment_photo_reports_api, name='equipment_photo_reports_api'),
]