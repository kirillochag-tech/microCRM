from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('generate-statistics/', views.generate_statistics, name='generate_statistics'),
    path('export-excel/', views.export_to_excel, name='export_excel'),
    path('task/<int:task_id>/analysis/', views.task_analysis, name='task_analysis'),
]