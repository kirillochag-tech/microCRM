# tasks/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.forms import TextInput, Textarea
from django.db import models
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404
from django.utils.html import format_html
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from nested_admin import NestedModelAdmin, NestedStackedInline, NestedTabularInline
from .models import (
    Task, TaskStatus, TaskType, SurveyQuestion,
    SurveyQuestionChoice, SurveyAnswer, PhotoReport, PhotoReportItem,
    SurveyAnswerPhoto, SurveyAnswerGroupReadStatus, EquipmentPhotoReport,
    TaskClientAssignment, TaskEmployeeAssignment, DailyTask
)
from .admin_forms import TaskAdminForm, DailyTaskForm
from django import forms
from users.models import CustomUser
from clients.models import Client
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Import the new API functions
from .views import getGroupedAnswers, markAsRead, autocomplete_clients, autocomplete_tasks, equipment_photo_reports_view, equipment_photo_reports_api

class SurveyQuestionChoiceInline(NestedTabularInline):
    """Inline choices for survey questions."""
    model = SurveyQuestionChoice
    extra = 0
    sortable_field_name = 'order'
    fields = ('choice_text', 'is_correct', 'order')
    verbose_name = _('Вариант ответа')
    verbose_name_plural = _('Варианты ответов')

class SurveyQuestionInline(NestedStackedInline):
    """Inline questions for survey tasks."""
    model = SurveyQuestion
    extra = 0
    inlines = [SurveyQuestionChoiceInline]
    verbose_name = _('Вопрос')
    verbose_name_plural = _('Вопросы')
    sortable_field_name = 'order'
    fields = ('question_text', 'question_type', 'order')
    classes = ['sortable']
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '80'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 80})},
    }

# SurveyQuestionChoice is hidden from admin as per requirements
# @admin.register(SurveyQuestionChoice)
# class SurveyQuestionChoiceAdmin(admin.ModelAdmin):
#     list_display = ('question', 'choice_text', 'order')
#     list_filter = ('question__task', 'question')
#     search_fields = ('choice_text', 'question__question_text')
#     ordering = ('question', 'order')

@admin.register(Task)
class TaskAdmin(NestedModelAdmin):
    form = TaskAdminForm
    list_display = ('title', 'task_type', 'status', 'is_active', 
                   'created_by', 'created_at',
                   'get_completion_info')
    list_filter = ('task_type', 'status', 'is_active', 'client_group', 'employee_group', 'created_by')
    search_fields = ('title', 'description')
    list_per_page = 20
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('title', 'description', 'task_type', 'status', 'is_active')
        }),
        (_('Назначение'), {
            'fields': ('created_by', 'employee_group', 'client_group', 'assigned_employees', 'assigned_clients'),
            'classes': ('collapse',)  # Make this fieldset collapsible
        }),
        (_('План выполнения'), {
            'fields': ('target_count',),
            'classes': ('collapse',)
        }),
        (_('Дополнительно'), {
            'fields': ('moderator_comment',),
            'classes': ('collapse',)
        }),
    )
    
    def get_inlines(self, request, obj=None):
        if obj and obj.task_type == TaskType.SURVEY:
            return [SurveyQuestionInline]
        elif obj and obj.task_type in [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]:
            return []
        return []
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'assigned_to', 'client', 'created_by'
        )
    
    def save_model(self, request, obj, form, change):
        """Сохраняет объект с установкой создателя при создании новой задачи."""
        if not change:  # При создании новой задачи
            obj.created_by = request.user
            # Устанавливаем статус в SENT (В работе) для новых задач, а не DRAFT
            obj.status = TaskStatus.SENT
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        """Сохраняет связанные объекты (назначения сотрудников и клиентов)."""
        # Сначала сохраняем стандартные связанные объекты
        super().save_related(request, form, formsets, change)
        
        # Получаем задачу
        task = form.instance
        
        # Очищаем существующие назначения
        TaskEmployeeAssignment.objects.filter(task=task).delete()
        TaskClientAssignment.objects.filter(task=task).delete()
        
        # Получаем данные из формы
        all_employees = set()
        all_clients = set()
        
        # Добавляем вручную выбранных сотрудников
        if 'assigned_employees' in form.cleaned_data:
            all_employees.update(emp.id for emp in form.cleaned_data['assigned_employees'])
        
        # Добавляем сотрудников из группы
        if 'employee_group' in form.cleaned_data and form.cleaned_data['employee_group']:
            group_employees = form.cleaned_data['employee_group'].customuser_set.filter(role='EMPLOYEE')
            all_employees.update(emp.id for emp in group_employees)
        
        # Добавляем вручную выбранных клиентов
        if 'assigned_clients' in form.cleaned_data:
            all_clients.update(client.id for client in form.cleaned_data['assigned_clients'])
        
        # Добавляем клиентов из группы
        if 'client_group' in form.cleaned_data and form.cleaned_data['client_group']:
            group_clients = form.cleaned_data['client_group'].client_set.all()
            all_clients.update(client.id for client in group_clients)
        
        # Создаем назначения сотрудников
        for employee_id in all_employees:
            try:
                employee = CustomUser.objects.get(id=employee_id)
                TaskEmployeeAssignment.objects.create(
                    task=task,
                    employee=employee
                )
            except CustomUser.DoesNotExist:
                continue
        
        # Создаем назначения клиентов
        for client_id in all_clients:
            try:
                client = Client.objects.get(id=client_id)
                TaskClientAssignment.objects.create(
                    task=task,
                    client=client
                )
            except Client.DoesNotExist:
                continue
    
    def get_completion_info(self, obj):
        if obj.task_type == TaskType.SURVEY:
            percentage = obj.get_completion_percentage()
            return format_html(
                '{} / {} ({}%)<br><a href="{}" class="btn btn-sm btn-info">📊 Статистика</a>',
                obj.current_count,
                obj.target_count,
                percentage,
                reverse('admin:survey_statistics', args=[obj.id])
            )
        return '-'
    get_completion_info.short_description = _('Выполнение')
    get_completion_info.allow_tags = True
    
    class Media:
        css = {
            'all': ('tasks/admin/survey_admin.css',)
        }
        js = ('tasks/admin/task_admin.js',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Убираем поле current_count из формы
        if 'current_count' in form.base_fields:
            del form.base_fields['current_count']
        
        # Устанавливаем значение по умолчанию для target_count
        if not obj:  # Только при создании новой задачи
            form.base_fields['target_count'].initial = 1
        
        return form

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('survey-stats/<int:task_id>/', 
                 self.admin_site.admin_view(self.survey_statistics_view), 
                 name='survey_statistics'),
        ]
        return custom_urls + urls
    
    def survey_statistics_view(self, request, task_id):
        """View for detailed survey statistics."""
        task = get_object_or_404(Task, id=task_id)
        
        # Общая статистика
        total_responses = SurveyAnswer.objects.filter(question__task=task).count()
        unique_clients = SurveyAnswer.objects.filter(question__task=task).values('client').distinct().count()
        
        # Статистика по вопросам
        questions_stats = []
        for question in task.questions.all():
            question_stats = {
                'question': question,
                'total_answers': SurveyAnswer.objects.filter(question=question).count()
            }
            
            # Обработка всех типов вопросов с выбором
            if question.question_type in ['RADIO', 'CHECKBOX', 'SELECT_SINGLE', 'SELECT_MULTIPLE']:
                choice_stats = []
                
                # 1. Обработка кастомных вариантов ответов (если есть)
                if question.has_custom_choices():
                    for choice in question.choices.all():
                        # Подсчет ответов для разных типов вопросов
                        if question.question_type == 'RADIO':
                            # Для радиокнопок - через selected_choices
                            count = SurveyAnswer.objects.filter(
                                question=question,
                                selected_choices=choice
                            ).count()
                        elif question.question_type == 'CHECKBOX':
                            # Для чекбоксов - через selected_choices
                            count = SurveyAnswer.objects.filter(
                                question=question,
                                selected_choices=choice
                            ).count()
                        elif question.question_type == 'SELECT_SINGLE':
                            # Для одиночного выбора - через text_answer (ID варианта)
                            count = SurveyAnswer.objects.filter(
                                question=question,
                                text_answer=str(choice.id)
                            ).count()
                        elif question.question_type == 'SELECT_MULTIPLE':
                            # Для множественного выбора - через text_answer (ID вариантов через запятую)
                            count = SurveyAnswer.objects.filter(
                                question=question,
                                text_answer__contains=str(choice.id)
                            ).count()
                        
                        percentage = (count / question_stats['total_answers'] * 100) if question_stats['total_answers'] > 0 else 0
                        # Округление до 0.5%
                        percentage = round(percentage * 2) / 2.0
                        choice_stats.append({
                            'choice': choice,
                            'count': count,
                            'percentage': percentage
                        })
                
                # 2. Обработка стандартных вариантов (если нет кастомных)
                else:
                    # Для вопросов с типом RADIO - стандартные варианты "Да" и "Нет"
                    if question.question_type == 'RADIO':
                        # Стандартные варианты "Да" и "Нет"
                        yes_count = SurveyAnswer.objects.filter(
                            question=question,
                            text_answer__iexact='да'
                        ).count()
                        no_count = SurveyAnswer.objects.filter(
                            question=question,
                            text_answer__iexact='нет'
                        ).count()
                        
                        yes_percentage = (yes_count / question_stats['total_answers'] * 100) if question_stats['total_answers'] > 0 else 0
                        no_percentage = (no_count / question_stats['total_answers'] * 100) if question_stats['total_answers'] > 0 else 0
                        # Округление до 0.5%
                        yes_percentage = round(yes_percentage * 2) / 2.0
                        no_percentage = round(no_percentage * 2) / 2.0
                        
                        choice_stats.extend([
                            {
                                'choice': type('Choice', (), {'choice_text': 'Да'}),
                                'count': yes_count,
                                'percentage': yes_percentage
                            },
                            {
                                'choice': type('Choice', (), {'choice_text': 'Нет'}),
                                'count': no_count,
                                'percentage': no_percentage
                            }
                        ])
                    # Для вопросов с типом CHECKBOX - стандартные варианты "Да" и "Нет"
                    elif question.question_type == 'CHECKBOX':
                        # Стандартные варианты "Да" и "Нет"
                        yes_count = SurveyAnswer.objects.filter(
                            question=question,
                            text_answer__icontains='да'
                        ).count()
                        no_count = SurveyAnswer.objects.filter(
                            question=question,
                            text_answer__icontains='нет'
                        ).count()
                        
                        yes_percentage = (yes_count / question_stats['total_answers'] * 100) if question_stats['total_answers'] > 0 else 0
                        no_percentage = (no_count / question_stats['total_answers'] * 100) if question_stats['total_answers'] > 0 else 0
                        # Округление до 0.5%
                        yes_percentage = round(yes_percentage * 2) / 2.0
                        no_percentage = round(no_percentage * 2) / 2.0
                        
                        choice_stats.extend([
                            {
                                'choice': type('Choice', (), {'choice_text': 'Да'}),
                                'count': yes_count,
                                'percentage': yes_percentage
                            },
                            {
                                'choice': type('Choice', (), {'choice_text': 'Нет'}),
                                'count': no_count,
                                'percentage': no_percentage
                            }
                        ])
                
                question_stats['choice_stats'] = choice_stats
                
            # Текстовые вопросы
            elif question.question_type in ['TEXT', 'TEXT_SHORT', 'TEXTAREA']:
                text_answers = SurveyAnswer.objects.filter(
                    question=question
                ).exclude(text_answer__isnull=True).exclude(text_answer='')
                question_stats['text_answers_count'] = text_answers.count()
                
            # Фото вопросы
            elif question.question_type == 'PHOTO':
                # Получаем все ответы с фото для этого вопроса
                answers_with_photos = SurveyAnswer.objects.filter(
                    question=question
                ).prefetch_related('photos', 'client').order_by('client__name', 'created_at')
                
                # Группируем фото по ответам (клиентам)
                photo_groups = []
                for answer in answers_with_photos:
                    photos_data = []
                    for photo in answer.photos.all():
                        # Попытка извлечь EXIF данные
                        exif_data = self._extract_photo_exif(photo.photo.path) if photo.photo else None
                        address = self._format_address_from_exif(exif_data) if exif_data else None
                        
                        photos_data.append({
                            'photo': photo,
                            'client': answer.client,
                            'created_at': answer.created_at,
                            'exif_data': exif_data,
                            'address': address
                        })
                    
                    if photos_data:
                        photo_groups.append({
                            'answer': answer,
                            'photos_data': photos_data
                        })
                
                question_stats['photo_groups'] = photo_groups
                question_stats['total_photos'] = sum(len(group['photos_data']) for group in photo_groups)
            
            questions_stats.append(question_stats)
        
        context = {
            'title': f'Статистика: {task.title}',
            'task': task,
            'total_responses': total_responses,
            'unique_clients': unique_clients,
            'questions_stats': questions_stats,
            'opts': self.model._meta,
        }
        return render(request, 'admin/tasks/survey_statistics.html', context)

    def _extract_photo_exif(self, photo_path):
        """Извлекает EXIF данные из фото."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            img = Image.open(photo_path)
            exifdata = img.getexif()
            if exifdata:
                exif = {}
                for tag_id in exifdata:
                    tag = TAGS.get(tag_id, tag_id)
                    data = exifdata.get(tag_id)
                    if isinstance(data, bytes):
                        data = data.decode()
                    exif[tag] = data
                return exif
        except Exception as e:
            print(f"Error extracting EXIF: {e}")
        return None

    def _format_address_from_exif(self, exif_data):
        """Форматирует адрес из EXIF данных."""
        if not exif_data:
            return None
        
        try:
            # Извлечение координат из GPS данных
            gps_info = exif_data.get('GPSInfo')
            if gps_info:
                # Извлечение GPS-координат
                gps_keys = list(gps_info.keys())
                gps_values = list(gps_info.values())
                
                # Извлечение широты и долготы
                lat = self._convert_to_degrees(gps_info.get(2), gps_info.get(1))  # GPSLatitude, GPSLatitudeRef
                lon = self._convert_to_degrees(gps_info.get(4), gps_info.get(3))  # GPSLongitude, GPSLongitudeRef
                
                if lat and lon:
                    return f"{lat}, {lon}"
        except Exception as e:
            print(f"Error formatting address from EXIF: {e}")
        
        return None

    def _convert_to_degrees(self, value, ref):
        """Конвертирует GPS-координаты в градусы."""
        if not value:
            return None
        
        try:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            
            degrees = d + (m / 60.0) + (s / 3600.0)
            
            if ref in ['S', 'W']:
                degrees = -degrees
                
            return degrees
        except (IndexError, ValueError, TypeError):
            return None

# Остальные регистрации моделей...
class SurveyAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'client', 'get_selected_choices', 'text_answer_preview', 'has_photos', 'created_at')
    readonly_fields = ('user', 'question', 'selected_choices', 'text_answer', 'client', 'created_at')
    list_per_page = 20
    change_list_template = 'admin/tasks/grouped_survey_answers.html'
    
    # Add filters
    list_filter = (
        'created_at',
        'user', 
        'question__task',
        'question',
        'client',
    )
    
    # Search fields for autocomplete functionality
    search_fields = (
        'client__name__icontains',  # For client search
        'user__username__icontains',  # For user search
        'user__first_name__icontains',  # For user first name
        'user__last_name__icontains',  # For user last name
        'question__task__title__icontains',  # For task search
        'question__question_text__icontains',  # For question search
    )
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_selected_choices(self, obj):
        if obj.selected_choices.exists():
            return ', '.join([choice.choice_text for choice in obj.selected_choices.all()])
        return '-'
    get_selected_choices.short_description = _('Выбранные варианты')
    
    def text_answer_preview(self, obj):
        if obj.text_answer:
            return obj.text_answer[:50] + '...' if len(obj.text_answer) > 50 else obj.text_answer
        return '-'
    text_answer_preview.short_description = _('Текстовый ответ')
    
    def has_photos(self, obj):
        return obj.photos.exists()
    has_photos.short_description = _('Есть фото')
    has_photos.boolean = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'question', 'client').prefetch_related('photos', 'selected_choices')

    def changelist_view(self, request, extra_context=None):
        """Override the default changelist view to use our grouped view"""
        from clients.models import Client
        from users.models import CustomUser
        from .models import Task
        
        clients = Client.objects.all()
        users = CustomUser.objects.filter(role='EMPLOYEE')
        moderators = CustomUser.objects.filter(role='MODERATOR')
        tasks = Task.objects.all()
        
        context = {
            'clients': clients,
            'users': users,
            'moderators': moderators,
            'tasks': tasks,
            'current_filters': request.GET,
            'opts': self.model._meta,
        }
        context.update(extra_context or {})
        
        return render(request, 'admin/tasks/grouped_survey_answers.html', context)

    def get_urls(self):
        urls = super().get_urls()
        # Remove the default changelist URL and replace with our custom functionality
        custom_urls = [
            path('export-excel/<int:task_id>/',
                 self.admin_site.admin_view(self.export_excel_view),
                 name='export_survey_answers_excel'),
            path('api/grouped-answers/',
                 getGroupedAnswers,
                 name='grouped_answers_api'),
            path('api/mark-as-read/',
                 markAsRead,
                 name='mark_as_read_api'),
            path('equipment-photo-reports/',
                 self.admin_site.admin_view(equipment_photo_reports_view),
                 name='equipment_photo_reports'),
            path('api/equipment-photo-reports/',
                 equipment_photo_reports_api,
                 name='equipment_photo_reports_api'),
        ]
        return custom_urls + urls

    def export_excel_view(self, request, task_id):
        """Export survey answers for a specific task to Excel."""
        from .models import Task
        
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return HttpResponse("Task not found", status=404)
        
        # Get all answers for this task
        answers = SurveyAnswer.objects.filter(
            question__task=task
        ).select_related(
            'user', 'question', 'client'
        ).prefetch_related(
            'photos', 'selected_choices'
        ).order_by('client__name', 'question__order', 'created_at')
        
        # Create Excel workbook
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = f"Ответы {task.title[:30]}"  # Limit sheet name length
        
        # Define headers
        headers = [
            'Клиент', 'Сотрудник', 'Дата ответа', 'Вопрос', 'Тип вопроса', 
            'Выбранные варианты', 'Текстовый ответ', 'Количество фото'
        ]
        
        # Write headers
        for col_num, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Write data
        row_num = 2
        for answer in answers:
            # Get selected choices as text
            selected_choices_text = ', '.join([choice.choice_text for choice in answer.selected_choices.all()])
            
            # Count photos
            photo_count = answer.photos.count()
            
            row_data = [
                answer.client.name,
                answer.user.get_full_name() or answer.user.username,
                answer.created_at.strftime('%d.%m.%Y %H:%M:%S'),
                answer.question.question_text,
                answer.question.get_question_type_display(),
                selected_choices_text,
                answer.text_answer,
                photo_count
            ]
            
            for col_num, value in enumerate(row_data, 1):
                cell = worksheet.cell(row=row_num, column=col_num, value=str(value) if value is not None else '')
                cell.alignment = Alignment(wrap_text=True, vertical='top')
            
            row_num += 1
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)  # Limit width to 50
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Prepare response
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="survey_answers_{task.title.replace(" ", "_")}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        workbook.save(response)
        return response

# @admin.register(SurveyAnswerGroupReadStatus)
# class SurveyAnswerGroupReadStatusAdmin(admin.ModelAdmin):
#     list_display = ('task', 'client', 'user', 'date_created', 'read_at', 'read_by')
#     list_filter = ('date_created', 'read_at', 'task', 'client', 'user')
#     search_fields = ('task__title', 'client__name', 'user__username')
#     readonly_fields = ('created_at',)
#     list_per_page = 20


@admin.register(SurveyAnswer)
class SurveyAnswerAdminWrapper(SurveyAnswerAdmin):
    pass


# Custom admin class to add equipment photo reports link
class PhotoReportItemInline(admin.TabularInline):
    """Inline admin for photo report items."""
    model = PhotoReportItem
    extra = 0
    readonly_fields = ('photo_preview', 'photo', 'description', 'quality_score', 'is_accepted', 'latitude', 'longitude', 'location_address', 'created_at')

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.photo.url)
        return _("Нет фото")
    photo_preview.short_description = _("Предпросмотр фото")


class PhotoReportAdmin(admin.ModelAdmin):
    list_display = ('task', 'client', 'address', 'stand_count', 'created_by', 'created_at')
    readonly_fields = ('task', 'client', 'address', 'stand_count', 'comment', 'created_by')
    inlines = [PhotoReportItemInline]
    list_per_page = 20


@admin.register(PhotoReportItem)
class PhotoReportItemAdmin(admin.ModelAdmin):
    list_display = ('report', 'photo_preview', 'latitude', 'longitude', 'location_address', 'created_at')
    readonly_fields = ('photo_preview', 'report', 'photo', 'description', 'quality_score', 'is_accepted', 
                       'latitude', 'longitude', 'location_address', 'created_at')
    list_filter = ('created_at', 'report__task', 'report__client')
    list_per_page = 20

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.photo.url)
        return _("Нет фото")
    photo_preview.short_description = _("Предпросмотр фото")


class EquipmentPhotoReportsAdmin(PhotoReportAdmin):
    """Admin class for equipment photo reports link."""
    
    def has_module_permission(self, request):
        # Show to all users who can access photo reports
        return request.user.is_superuser or (hasattr(request.user, 'role') and 
               (request.user.role == 'MODERATOR' or request.user.role == 'EMPLOYEE'))
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow access to the view but not direct changes to objects
        return self.has_module_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        # Redirect to our custom view
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(reverse('admin:equipment_photo_reports'))
    
    def get_model_perms(self, request):
        # Show the model in the admin menu
        perms = super().get_model_perms(request)
        if self.has_module_permission(request):
            perms['add'] = False
            perms['change'] = True
            perms['delete'] = False
        else:
            perms = {}
        return perms



# Register the custom admin with EquipmentPhotoReport proxy model to create the equipment photo reports link
admin.site.register(EquipmentPhotoReport, EquipmentPhotoReportsAdmin)

# Register assignment models
# @admin.register(TaskClientAssignment)
# class TaskClientAssignmentAdmin(admin.ModelAdmin):
#     list_display = ('task', 'client', 'created_at')
#     list_filter = ('task', 'client', 'created_at')
#     search_fields = ('task__title', 'client__name')

# @admin.register(TaskEmployeeAssignment)
# class TaskEmployeeAssignmentAdmin(admin.ModelAdmin):
#     list_display = ('task', 'employee', 'completed', 'completed_at', 'created_at')
#     list_filter = ('task', 'employee', 'completed', 'created_at')
#     search_fields = ('task__title', 'employee__username', 'employee__first_name', 'employee__last_name')

# Admin class for task statistics list
from django.urls import reverse
from .models import TaskSurveyStatsProxy, TaskType

class TaskStatisticsListAdmin(admin.ModelAdmin):
    list_display = ()  # Hide default list
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_view_permission(self, request, obj=None):
        return True
    
    def changelist_view(self, request, extra_context=None):
        from .models import Task
        survey_tasks = Task.objects.filter(task_type=TaskType.SURVEY).select_related(
            'created_by', 'client'
        ).order_by('-created_at')
        
        extra_context = extra_context or {}
        extra_context['survey_tasks'] = survey_tasks
        extra_context['title'] = 'Статистики задач'
        
        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(TaskSurveyStatsProxy, TaskStatisticsListAdmin)


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    form = DailyTaskForm
    list_display = ('date', 'client', 'creator', 'assignee', 'status_display', 'priority_display', 'created_at')
    list_filter = ('status', 'date', 'creator', 'assignee', 'priority')
    search_fields = ('client__name', 'creator__username', 'assignee__username', 'description')
    readonly_fields = ('created_at', 'updated_at', 'creator')
    list_per_page = 20
    change_form_template = 'admin/tasks/dailytask_form.html'
    change_list_template = 'admin/tasks/dailytask_changelist.html'
    
    # Отключаем массовые действия для этой страницы
    actions_on_top = False
    actions_on_bottom = False
    
    class Media:
        css = {
            'all': ('tasks/admin/dailytask_admin.css',)
        }

    fieldsets = (
        (_('Основная информация'), {
            'fields': ('date', 'creator', 'assignee', 'status', 'priority')
        }),
        (_('Описание и результат'), {
            'fields': ('description', 'result')
        }),
        (_('Дополнительно'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'client', 'creator', 'assignee'
        )
        return qs.order_by('-date')

    def changelist_view(self, request, extra_context=None):
        """Add additional context for the custom changelist template."""
        from django.contrib.admin.views.main import ChangeList
        from users.models import CustomUser
        
        extra_context = extra_context or {}
        
        # Удаляем параметр 'grouped' из запроса перед передачей в ChangeList
        # чтобы Django не пытался использовать его как поле фильтрации
        request_get = request.GET.copy()
        if 'grouped' in request_get:
            del request_get['grouped']
        request.GET = request_get
        
        # Получаем ChangeList для применения фильтров
        cl = self.get_changelist_instance(request)
        
        # Используем отфильтрованный queryset из cl для карточек
        extra_context['tasks'] = cl.queryset
        
        # Добавляем список сотрудников для фильтра
        extra_context['employees'] = CustomUser.objects.filter(role='EMPLOYEE').order_by('first_name', 'last_name')
        
        response = super().changelist_view(request, extra_context)
        return response

    def get_form(self, request, obj=None, **kwargs):
        """Pass request to the form for automatic creator assignment."""
        form = super().get_form(request, obj, **kwargs)
        
        class RequestForm(form):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return super().__new__(cls)
        
        return RequestForm

    def save_model(self, request, obj, form, change):
        """Set creator when creating a new DailyTask."""
        if not change and not obj.creator_id:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def status_display(self, obj):
        """Display status with color coding."""
        status_colors = {
            'active': '#28a745',
            'completed': '#6c757d',
            'hidden': '#dc3545',
        }
        color = status_colors.get(obj.status, '#6c757d')
        status_labels = {
            'active': 'Активная',
            'completed': 'Завершенная',
            'hidden': 'Скрытая',
        }
        label = status_labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, label
        )
    status_display.short_description = 'Статус'

    def priority_display(self, obj):
        """Display priority with color coding."""
        priority_colors = {
            1: '#17a2b8',
            2: '#ffc107',
            3: '#dc3545',
        }
        color = priority_colors.get(obj.priority, '#6c757d')
        priority_labels = {
            1: 'Низкий',
            2: 'Средний',
            3: 'Высокий',
        }
        label = priority_labels.get(obj.priority, str(obj.priority))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, label
        )
    priority_display.short_description = 'Приоритет'