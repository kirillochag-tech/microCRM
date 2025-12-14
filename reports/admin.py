"""
Admin interface for reporting and analytics.

This module provides comprehensive reporting interface with filters
and data visualization capabilities.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.db.models import Count, Q
from django.core.paginator import Paginator
import json

# from .models import TaskStatistics
from tasks.models import Task, SurveyAnswer, SurveyQuestion, PhotoReport, PhotoReportItem
from users.models import CustomUser
from clients.models import Client, ClientGroup

# class TaskStatisticsFilter(admin.SimpleListFilter):
#     """Custom filter for task statistics."""
#     title = _('Тип задачи')
#     parameter_name = 'task_type'

#     def lookups(self, request, model_admin):
#         return [
#             ('SURVEY', _('Анкеты')),
#             ('PHOTO', _('Фотоотчеты')),
#         ]

#     def queryset(self, request, queryset):
#         if self.value() == 'SURVEY':
#             return queryset.filter(task__task_type='SURVEY')
#         if self.value() == 'PHOTO':
#             return queryset.filter(
#                 Q(task__task_type='EQUIPMENT_PHOTO') | 
#                 Q(task__task_type='SIMPLE_PHOTO')
#             )
#         return queryset

# @admin.register(TaskStatistics)
# class TaskStatisticsAdmin(admin.ModelAdmin):
#     """
#     Admin interface for task statistics.
    
#     Provides comprehensive reporting with filters and detailed views.
#     """
    
#     list_display = ('task', 'client', 'employee', 'total_responses', 'completed_tasks', 'last_updated')
#     list_filter = (
#         TaskStatisticsFilter,
#         'client', 
#         'employee', 
#         'moderator', 
#         'client_group', 
#         'last_updated'
#     )
#     search_fields = ('task__title', 'client__name', 'employee__username')
#     readonly_fields = ('survey_stats_display', 'photo_gallery_display')
    
#     change_list_template = 'admin/reports/taskstatistics/change_list.html'
    
#     def has_add_permission(self, request):
#         return False
    
#     def has_delete_permission(self, request, obj=None):
#         return False
    
#     def has_change_permission(self, request, obj=None):
#         return False
    
#     def survey_stats_display(self, obj):
#         """Display survey statistics in admin detail view."""
#         if obj.survey_stats:
#             stats_html = '<div class="survey-stats">'
#             for question_id, stats in obj.survey_stats.items():
#                 stats_html += f'<h5>{stats.get("question_text", "Вопрос")}</h5>'
#                 stats_html += '<ul>'
#                 for answer, count in stats.get('answers', {}).items():
#                     percentage = stats.get('total', 1) and (count / stats['total']) * 100 or 0
#                     stats_html += f'<li>{answer}: {count} ({percentage:.1f}%)</li>'
#                 stats_html += '</ul>'
#             stats_html += '</div>'
#             return stats_html
#         return '-'
#     survey_stats_display.short_description = _('Статистика анкет')
#     survey_stats_display.allow_tags = True
    
#     def photo_gallery_display(self, obj):
#         """Display photo gallery for photo reports."""
#         if obj.task.task_type in ['EQUIPMENT_PHOTO', 'SIMPLE_PHOTO']:
#             # Get all photos for this client/employee
#             photos = PhotoReportItem.objects.filter(
#                 report__client=obj.client,
#                 report__created_by=obj.employee
#             ).select_related('report')[:20]
            
#             gallery_html = '<div class="photo-gallery" style="display: flex; flex-wrap: wrap; gap: 10px;">'
#             for photo in photos:
#                 gallery_html += f'''
#                 <div style="width: 150px;">
#                     <img src="{photo.photo.url}" style="width: 100%; height: 100px; object-fit: cover;" 
#                          title="Отчет от {photo.created_at.strftime('%d.%m.%Y')}">
#                     <small>{photo.description or 'Без описания'}</small>
#                 </div>
#                 '''
#             gallery_html += '</div>'
#             return gallery_html
#         return '-'
#     photo_gallery_display.short_description = _('Фотогалерея')
#     photo_gallery_display.allow_tags = True

# Дополнительные админ-классы для прямого просмотра результатов

class SurveyAnswerInline(admin.TabularInline):
    """Inline for survey answers with statistics."""
    model = SurveyAnswer
    fields = ('user', 'question', 'text_answer_preview', 'has_photo')
    readonly_fields = ('user', 'question', 'text_answer_preview', 'has_photo')
    can_delete = False
    
    def text_answer_preview(self, obj):
        if obj.text_answer:
            return obj.text_answer[:50] + '...' if len(obj.text_answer) > 50 else obj.text_answer
        return '-'
    text_answer_preview.short_description = _('Ответ')
    
    def has_photo(self, obj):
        return bool(obj.photo)
    has_photo.short_description = _('Фото')
    has_photo.boolean = True

