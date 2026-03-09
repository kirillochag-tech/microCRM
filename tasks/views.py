# -*- coding: utf-8 -*-
"""
Task management views.

This module provides views for displaying and managing tasks.
Follows SOLID principles by separating concerns and providing clear interfaces.
"""
import re
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from .forms import SurveyResponseForm, AddPhotosForm, AddSinglePhotoForm, PhotoReportForm
from .models import Task, TaskStatus, TaskType, SurveyAnswer, SurveyQuestion, SurveyAnswerPhoto, PhotoReport, PhotoReportItem
from users.models import CustomUser, EmployeeGroup
from clients.models import Client, ClientGroup

from django.db.models import Count, Sum, Avg, Q
from django.core.exceptions import PermissionDenied


class TaskListView(LoginRequiredMixin, ListView):
    """
    View for displaying list of active tasks.
    """
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    def get_queryset(self):
        """Get queryset of active tasks for current user."""
        user = self.request.user
        if user.role == 'EMPLOYEE':
            # Get tasks where user is assigned or no specific assignment
            queryset = Task.objects.filter(
                status__in=[TaskStatus.SENT,
                            TaskStatus.REWORK, TaskStatus.ON_CHECK],
                is_active=True
            ).filter(
                Q(assigned_to=user) |
                Q(assigned_to__isnull=True) |
                Q(taskemployeeassignment__employee=user)
            ).distinct().order_by('-created_at')
        elif user.role == 'MODERATOR':
            queryset = Task.objects.all().order_by('-created_at')
        else:
            return Task.objects.none()

        # Добавляем аннотацию для определения типа назначения клиента
        for task in queryset:
            if not task.taskclientassignment_set.exists() and not task.client:
                # Задача не имеет конкретных назначений - считаем, что для всех клиентов
                task.client_display_type = 'all_clients'
            elif task.client:
                # Старый способ: прямое назначение
                task.client_display_type = 'single_client'
                task.display_client_name = task.client.name
            elif task.taskclientassignment_set.exists():
                assigned_count = task.taskclientassignment_set.count()
                if assigned_count == 1:
                    # Новый способ: один клиент через назначение
                    task.client_display_type = 'single_client'
                    task.display_client_name = task.taskclientassignment_set.first().client.name
                else:
                    # Новый способ: несколько клиентов
                    task.client_display_type = 'multiple_clients'
                    task.display_client_count = assigned_count
                    # Добавляем статистику для фотоотчётов
                    if task.task_type in [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]:
                        from .models import PhotoReport
                        submitted_count = PhotoReport.objects.filter(task=task).values_list(
                            'client_id', flat=True).distinct().count()
                        task.total_clients = assigned_count
                        task.submitted_clients = submitted_count
            else:
                task.client_display_type = 'unknown'

        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Список задач')
        context['user_role'] = self.request.user.role
        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying details of a single task.
    """
    model = Task
    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'

    def get_object(self, queryset=None):
        """Get the task object with permission check."""
        task = super().get_object(queryset)
        if not task.can_be_viewed_by(self.request.user):
            raise Http404(_("Задача не найдена или недоступна"))
        return task

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Детали задачи')
        context['can_edit'] = self.object.can_be_edited_by(self.request.user)

        # Для фотоотчётов показываем статус клиентов
        if context['task'].task_type in [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]:
            from .models import PhotoReport
            submitted_client_ids = list(
                PhotoReport.objects.filter(
                    task=context['task']).values_list('client_id', flat=True)
            )
            context['submitted_client_ids'] = submitted_client_ids

        # Определяем клиента для отображения
        if not context['task'].client and context['task'].taskclientassignment_set.exists():
            assigned_clients = context['task'].taskclientassignment_set.all()
            if assigned_clients.count() == 1:
                # Если только один клиент в назначении, используем его для отображения
                context['display_client'] = assigned_clients.first().client

        # Добавляем статистику для фотоотчётов
        if context['task'].task_type in [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]:
            total_clients = len(context['task'].get_assigned_clients())
            if total_clients > 0:
                from .models import PhotoReport
                submitted_clients = PhotoReport.objects.filter(
                    task=context['task']).values_list('client_id', flat=True).distinct().count()
                context['total_clients'] = total_clients
                context['submitted_clients'] = submitted_clients
                context['completion_percentage'] = context['task'].get_photo_completion_percentage()

        if context['task'].task_type == TaskType.SURVEY:
            context['completion_percentage'] = context['task'].get_completion_percentage()

        return context

    def post(self, request, *args, **kwargs):
        """Handle task completion."""
        task = self.get_object()
        if task.can_be_edited_by(request.user) or (request.user.role == 'EMPLOYEE' and task.assigned_to == request.user):
            task.status = TaskStatus.COMPLETED
            task.is_active = False
            task.save()
            messages.success(request, _("Задача успешно завершена!"))
            return HttpResponseRedirect(reverse('tasks:task_list'))
        return self.get(request, *args, **kwargs)


class SurveyResponseView(LoginRequiredMixin, FormView):
    """
    Представление для заполнения анкеты.
    """
    template_name = 'tasks/survey_form.html'
    form_class = SurveyResponseForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        task_id = self.kwargs['task_id']
        task = get_object_or_404(Task, id=task_id)
        if not task.can_be_viewed_by(self.request.user):
            raise Http404(_("Задача не найдена или недоступна"))
        # Allow only survey tasks (not photo reports as they need a different form)
        if task.task_type != TaskType.SURVEY:
            raise Http404(_("Задача не является анкетой"))
        kwargs['task'] = task
        kwargs['user'] = self.request.user
        return kwargs

    # В SurveyResponseView метод form_valid

    def form_valid(self, form):
        # Сохраняем анкету через форму, которая сама обновит current_count
        form.save()

        messages.success(self.request, _("Анкета успешно заполнена!"))
        return redirect('tasks:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task_id = self.kwargs['task_id']
        context['task'] = get_object_or_404(Task, id=task_id)
        context['title'] = _('Заполнение анкеты')

        # Определяем клиента для отображения (аналогично PhotoReportView)
        if not context['task'].client and context['task'].taskclientassignment_set.exists():
            assigned_clients = context['task'].taskclientassignment_set.all()
            if assigned_clients.count() == 1:
                context['display_client'] = assigned_clients.first().client

        return context


class PhotoReportView(LoginRequiredMixin, FormView):
    """
    View for filling photo report tasks.
    """
    template_name = 'tasks/photo_report_form.html'  # Need to create this template
    form_class = PhotoReportForm  # Using the new form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        task_id = self.kwargs['task_id']
        task = get_object_or_404(Task, id=task_id)
        if not task.can_be_viewed_by(self.request.user):
            raise Http404(_("Задача не найдена или недоступна"))
        if task.task_type not in [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]:
            raise Http404(_("Задача не является фотоотчетом"))
        kwargs['task'] = task
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        print("=== DEBUG: PhotoReportView.form_valid START ===")
        print(f"Form cleaned_data: {form.cleaned_data}")
        print(f"Request FILES: {self.request.FILES}")

        # Create the photo report
        task_id = self.kwargs['task_id']
        task = get_object_or_404(Task, id=task_id)
        print(f"Task ID: {task_id}, Task: {task}")

        client = None
        
        # Получаем данные из формы
        if 'client_id' in form.cleaned_data and form.cleaned_data['client_id']:
            # В случае задачи на одного клиента или autocomplete, client_id - это integer
            client_input = form.cleaned_data['client_id']
            print(f"Client input from form: {client_input}")

            # Определяем ID клиента, независимо от того, пришёл ли объект или ID
            if isinstance(client_input, Client):
                client_id = client_input.id
                client = client_input
            elif isinstance(client_input, int):
                client_id = client_input
                client = Client.objects.get(id=client_id)
            else:
                # Пытаемся конвертировать в int
                try:
                    client_id = int(client_input)
                    client = Client.objects.get(id=client_id)
                except (ValueError, Client.DoesNotExist):
                    messages.error(self.request, _("Не выбран клиент"))
                    return self.form_invalid(form)

            # Проверяем, назначен ли этот клиент на текущую задачу
            # Для задач "для всех клиентов" проверка не нужна
            if task.taskclientassignment_set.exists() or task.client:
                if not task.is_client_assigned(client_id):
                    messages.error(self.request, _(
                        f"Клиент '{client.name}' не назначен на эту задачу"))
                    print("=== DEBUG: Client not assigned to task ===")
                    return self.form_invalid(form)

        elif 'client' in form.cleaned_data and form.cleaned_data['client']:
            # Этот блок для задач со списком клиентов (старый вариант)
            client = form.cleaned_data['client']
            if not task.is_client_assigned(client.id):
                messages.error(self.request, _(
                    "Клиент не назначен на эту задачу"))
                print("=== DEBUG: Client not assigned to task (else branch) ===")
                return self.form_invalid(form)
        else:
            messages.error(self.request, _("Не выбран клиент"))
            return self.form_invalid(form)
        address = form.cleaned_data['address']
        stand_count = form.cleaned_data['stand_count']
        comment = form.cleaned_data['comment']
        print(f"Address: {address}, Stand Count: {
              stand_count}, Comment: {comment}")

        # Create photo report
        photo_report = PhotoReport.objects.create(
            task=task,
            client=client,
            address=address,
            stand_count=stand_count,
            comment=comment,
            created_by=self.request.user
        )
        print(f"=== DEBUG: PhotoReport created with ID: {photo_report.id} ===")

        # Handle photo uploads
        uploaded_files = self.request.FILES.getlist('photos')
        print(f"Number of uploaded files: {len(uploaded_files)}")
        for i, photo_file in enumerate(uploaded_files):
            print(f"Processing file {i+1}: {photo_file.name}")
            
            # Extract geolocation data from photo if available
            latitude = None
            longitude = None
            location_address = None
            
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS
                # Open the temporary file to read EXIF data
                img = Image.open(photo_file)
                exifdata = img.getexif()
                
                if exifdata:
                    exif_dict = {}
                    for tag_id in exifdata:
                        tag = TAGS.get(tag_id, tag_id)
                        data = exifdata.get(tag_id)
                        if isinstance(data, bytes):
                            try:
                                data = data.decode()
                            except:
                                data = str(data)
                        exif_dict[tag] = data

                    # Extract GPS coordinates
                    gps_info = exif_dict.get('GPSInfo')
                    
                    # Проверяем, есть ли GPS-информация и в каком формате она представлена
                    if gps_info:
                        # GPSInfo может быть числом (смещением) или словарем
                        # Если это число, нужно получить реальные GPS-данные из этого смещения
                        if isinstance(gps_info, int):
                            # Если gps_info - это число, это смещение в EXIF-данных
                            # Нужно получить реальные GPS-данные из этого смещения
                            try:
                                # Повторно открываем изображение и получаем GPSInfo напрямую
                                img_with_gps = Image.open(photo_file)
                                full_exif = img_with_gps.getexif()
                                gps_ifd = full_exif.get_ifd(0x8825)  # GPS IFD (Image File Directory)
                                
                                if gps_ifd:
                                    # Теперь работаем с GPS-данными как с обычным словарем
                                    gps_info = gps_ifd
                                else:
                                    print(f"Could not extract GPS IFD from offset {gps_info}")
                                    gps_info = None
                            except Exception as e:
                                print(f"Error getting GPS IFD from offset: {e}")
                                gps_info = None
                        
                        # Проверяем, что теперь gps_info - это словареподобный объект
                        if gps_info and hasattr(gps_info, 'get'):
                            try:
                                # Extract latitude
                                lat_ref = gps_info.get(1)  # GPSLatitudeRef
                                lat_values = gps_info.get(2)  # GPSLatitude
                                
                                if lat_values and len(lat_values) >= 3:
                                    # Handle rational numbers in EXIF data (represented as tuples)
                                    def rational_to_float(rational_val):
                                        if isinstance(rational_val, tuple) and len(rational_val) == 2:
                                            return float(rational_val[0]) / float(rational_val[1])
                                        elif isinstance(rational_val, (int, float)):
                                            return float(rational_val)
                                        else:
                                            return float(rational_val)
                                    
                                    lat_deg = rational_to_float(lat_values[0])
                                    lat_min = rational_to_float(lat_values[1])
                                    lat_sec = rational_to_float(lat_values[2])
                                    
                                    lat = lat_deg + (lat_min / 60.0) + (lat_sec / 3600.0)
                                    if lat_ref and lat_ref == 'S':
                                        lat = -lat
                                    latitude = lat
                                else:
                                    latitude = None

                                # Extract longitude
                                lon_ref = gps_info.get(3)  # GPSLongitudeRef
                                lon_values = gps_info.get(4)  # GPSLongitude
                                
                                if lon_values and len(lon_values) >= 3:
                                    # Handle rational numbers in EXIF data (represented as tuples)
                                    def rational_to_float(rational_val):
                                        if isinstance(rational_val, tuple) and len(rational_val) == 2:
                                            return float(rational_val[0]) / float(rational_val[1])
                                        elif isinstance(rational_val, (int, float)):
                                            return float(rational_val)
                                        else:
                                            return float(rational_val)
                                    
                                    lon_deg = rational_to_float(lon_values[0])
                                    lon_min = rational_to_float(lon_values[1])
                                    lon_sec = rational_to_float(lon_values[2])
                                    
                                    lon = lon_deg + (lon_min / 60.0) + (lon_sec / 3600.0)
                                    if lon_ref and lon_ref == 'W':
                                        lon = -lon
                                    longitude = lon
                                else:
                                    longitude = None

                                # Reverse geocode to get address if coordinates are available
                                if latitude is not None and longitude is not None:
                                    from .views import reverse_geocode
                                    location_address = reverse_geocode(latitude, longitude)
                                    if not location_address:
                                        location_address = 'Не удалось определить адрес'
                            except Exception as e:
                                print(f"Error extracting GPS coordinates: {e}")
                        else:
                            # Если GPSInfo не является словарем даже после попытки получить его из смещения
                            print(f"GPSInfo is not accessible as a dictionary: {type(gps_info)}, value: {gps_info}")
                            # Возможно, GPS-информация отсутствует в фото
                            latitude = None
                            longitude = None
                            location_address = None
                    else:
                        # Если GPSInfo вообще нет в EXIF-данных
                        print("No GPSInfo found in EXIF data")
                        latitude = None
                        longitude = None
                        location_address = None
                    
            except Exception as e:
                print(f"Error extracting EXIF data for photo {photo_file.name}: {e}")
            
            PhotoReportItem.objects.create(
                report=photo_report,
                photo=photo_file,
                latitude=latitude,
                longitude=longitude,
                location_address=location_address
            )

        # Сбрасываем статус задачи на исходный (SENT), если сотрудник отправляет новый отчёт
        # Это позволяет модератору повторно обработать отчёт
        if task.status in [TaskStatus.ON_CHECK, TaskStatus.REWORK, TaskStatus.ACCEPTED]:
            task.status = TaskStatus.SENT
        task.is_active = True
        task.save(update_fields=['status', 'is_active'])
        print(f"Task is_active set to: {
              task.is_active}, status reset to: {task.status}")

        messages.success(self.request, _("Фотоотчет успешно заполнен!"))
        print("=== DEBUG: PhotoReportView.form_valid END ===")
        return redirect('tasks:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task_id = self.kwargs['task_id']
        context['task'] = get_object_or_404(Task, id=task_id)
        context['title'] = _('Заполнение фотоотчета')

        # Для фотоотчётов показываем статус клиентов
        if context['task'].task_type in [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]:
            from .models import PhotoReport
            submitted_client_ids = list(
                PhotoReport.objects.filter(
                    task=context['task']).values_list('client_id', flat=True)
            )
            context['submitted_client_ids'] = submitted_client_ids

        # Определяем клиента для отображения
        if not context['task'].client and context['task'].taskclientassignment_set.exists():
            assigned_clients = context['task'].taskclientassignment_set.all()
            if assigned_clients.count() == 1:
                # Если только один клиент в назначении, используем его для отображения
                context['display_client'] = assigned_clients.first().client

        return context


class SurveyResultsView(LoginRequiredMixin, ListView):
    """
    View for displaying survey results.
    """
    template_name = 'tasks/survey_results.html'
    context_object_name = 'results'

    def get_queryset(self):
        task_id = self.kwargs['task_id']
        task = get_object_or_404(Task, id=task_id)

        # Получаем все ответы по этой задаче
        answers = SurveyAnswer.objects.filter(question__task=task)

        # Группируем по вопросам
        results = []
        for question in task.questions.all():
            question_results = {
                'question': question,
                'answers_count': answers.filter(question=question).count()
            }

            # Если это вопрос с вариантами ответов
            if question.has_custom_choices():
                choice_stats = {}
                for choice in question.choices.all():
                    count = answers.filter(selected_choices=choice).count()
                    choice_stats[choice.choice_text] = count
                question_results['choice_stats'] = choice_stats

            results.append(question_results)

        return results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task'] = get_object_or_404(Task, id=self.kwargs['task_id'])
        context['title'] = _('Результаты анкеты')
        return context


class TaskStatisticsView(LoginRequiredMixin, TemplateView):
    """
    View for displaying task statistics.
    """
    template_name = 'tasks/statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Статистика задач')
        context['total_tasks'] = Task.objects.count()
        context['completed_tasks'] = Task.objects.filter(
            status='COMPLETED').count()
        return context

# В конец файла tasks/views.py


class AddPhotosView(LoginRequiredMixin, FormView):
    """
    View for adding additional photos to existing survey answer.
    """
    template_name = 'tasks/add_photos.html'
    form_class = AddPhotosForm

    def get_answer(self):
        answer_id = self.kwargs['answer_id']
        return get_object_or_404(SurveyAnswer, id=answer_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        answer = self.get_answer()
        context['answer'] = answer
        context['current_photo_count'] = answer.photos.count()
        context['remaining_photos'] = max(0, 10 - answer.photos.count())
        return context

    # tasks/views.py - метод form_valid в AddPhotosView

    def form_valid(self, form):
        answer = self.get_answer()
        current_count = answer.photos.count()
        remaining_slots = 10 - current_count

        if remaining_slots <= 0:
            messages.error(self.request, _(
                "Максимальное количество фото (10) уже достигнуто."))
            return self.form_invalid(form)

        # ИСПРАВЛЕНО: используем self.request.FILES вместо self.files
        uploaded_files = self.request.FILES.getlist('photos')
        actual_upload_count = min(len(uploaded_files), remaining_slots)

        for i in range(actual_upload_count):
            SurveyAnswerPhoto.objects.create(
                answer=answer,
                photo=uploaded_files[i]
            )

        messages.success(self.request, _(
            f"Успешно добавлено {actual_upload_count} фото."))
        return redirect('tasks:survey_results', task_id=answer.question.task.id)


class AddSinglePhotoView(LoginRequiredMixin, FormView):
    """View for adding single photo to existing survey answer."""
    template_name = 'tasks/add_single_photo.html'
    form_class = AddSinglePhotoForm

    def get_answer(self):
        answer_id = self.kwargs['answer_id']
        return get_object_or_404(SurveyAnswer, id=answer_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        answer = self.get_answer()
        context['answer'] = answer
        return context

    def form_valid(self, form):
        answer = self.get_answer()
        if answer.photos.count() >= 10:
            messages.error(self.request, _(
                "Максимальное количество фото (10) уже достигнуто."))
            return self.form_invalid(form)

        # Создаем новое фото
        SurveyAnswerPhoto.objects.create(
            answer=answer,
            photo=form.cleaned_data['photo']
        )

        messages.success(self.request, _("Фото успешно добавлено."))
        return redirect('tasks:survey_results', task_id=answer.question.task.id)


class MySurveysView(LoginRequiredMixin, ListView):
    """
    View for displaying all surveys filled by employee.
    """
    template_name = 'tasks/my_surveys.html'
    context_object_name = 'surveys'

    def get_queryset(self):
        # Получаем все анкеты, где сотрудник участвовал
        return Task.objects.filter(
            task_type=TaskType.SURVEY,
            answers__user=self.request.user
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Мои анкеты')
        return context


class StatisticsView(LoginRequiredMixin, TemplateView):
    """
    Главная страница статистики с фильтрами и визуализацией.
    """
    template_name = 'tasks/statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Статистика задач')

        # Фильтры
        filters = self.request.GET

        # Базовый QuerySet
        tasks = Task.objects.all()

        # Применяем фильтры
        if 'task_type' in filters and filters['task_type'] != 'all':
            tasks = tasks.filter(task_type=filters['task_type'])

        if 'client' in filters and filters['client'] != 'all':
            tasks = tasks.filter(client_id=filters['client'])

        if 'employee' in filters and filters['employee'] != 'all':
            tasks = tasks.filter(assigned_to_id=filters['employee'])

        if 'moderator' in filters and filters['moderator'] != 'all':
            tasks = tasks.filter(created_by_id=filters['moderator'])

        if 'group_client' in filters and filters['group_client'] != 'all':
            # Здесь можно добавить фильтрацию по группам клиентов
            pass

        if 'date_from' in filters:
            tasks = tasks.filter(created_at__gte=filters['date_from'])

        if 'date_to' in filters:
            tasks = tasks.filter(created_at__lte=filters['date_to'])

        # Статистика по всем задачам
        context['total_tasks'] = tasks.count()
        context['completed_tasks'] = tasks.filter(status='COMPLETED').count()
        context['on_check_tasks'] = tasks.filter(status='ON_CHECK').count()
        context['sent_tasks'] = tasks.filter(status='SENT').count()

        # Статистика по типам задач
        context['survey_tasks'] = tasks.filter(task_type='SURVEY').count()
        context['photo_tasks'] = tasks.filter(
            task_type__in=['EQUIPMENT_PHOTO', 'SIMPLE_PHOTO']).count()

        # Статистика по сотрудникам
        context['employees_stats'] = CustomUser.objects.filter(role='EMPLOYEE').annotate(
            total_tasks=Count('tasks_assigned'),
            completed_tasks=Count('tasks_assigned', filter=Q(
                tasks_assigned__status='COMPLETED')),
            on_check_tasks=Count('tasks_assigned', filter=Q(
                tasks_assigned__status='ON_CHECK'))
        ).order_by('-total_tasks')

        # Статистика по клиентам
        context['clients_stats'] = Client.objects.annotate(
            total_tasks=Count('tasks'),
            completed_tasks=Count(
                'tasks', filter=Q(tasks__status='COMPLETED')),
            on_check_tasks=Count('tasks', filter=Q(tasks__status='ON_CHECK'))
        ).order_by('-total_tasks')

        # Статистика по анкетам
        survey_tasks = tasks.filter(task_type='SURVEY')
        context['survey_statistics'] = []

        for task in survey_tasks:
            total_answers = SurveyAnswer.objects.filter(
                question__task=task).count()
            unique_clients = SurveyAnswer.objects.filter(
                question__task=task).values('client').distinct().count()
            completion_rate = 0

            if task.target_count > 0:
                completion_rate = min(
                    100, int((task.current_count / task.target_count) * 100))

            context['survey_statistics'].append({
                'task': task,
                'total_answers': total_answers,
                'unique_clients': unique_clients,
                'completion_rate': completion_rate
            })

        # График для первой анкеты
        if context['survey_statistics']:
            first_survey = context['survey_statistics'][0]
            context['first_survey_chart_data'] = self.get_chart_data(
                first_survey['task'])

        return context

    def get_chart_data(self, task):
        """Получает данные для графика по первой анкете."""
        data = {
            'labels': [],
            'datasets': [{
                'label': 'Количество ответов',
                'data': [],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)'
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                'borderWidth': 1
            }]
        }

        # Получаем все вопросы анкеты
        questions = task.questions.all()

        for question in questions:
            data['labels'].append(question.question_text[:30])
            answers_count = SurveyAnswer.objects.filter(
                question=question).count()
            data['datasets'][0]['data'].append(answers_count)

        return data


def survey_statistics_view(self, request, task_id):
    """View for detailed survey statistics."""
    task = get_object_or_404(Task, id=task_id)

    # Общая статистика
    total_responses = SurveyAnswer.objects.filter(question__task=task).count()
    unique_clients = SurveyAnswer.objects.filter(
        question__task=task).values('client').distinct().count()

    # Статистика по вопросам
    questions_stats = []
    for question in task.questions.all():
        question_stats = {
            'question': question,
            'total_answers': SurveyAnswer.objects.filter(question=question).count()
        }

        if question.has_custom_choices():
            choice_stats = []
            for choice in question.choices.all():
                count = SurveyAnswer.objects.filter(
                    question=question,
                    selected_choices=choice
                ).count()
                percentage = (
                    count / question_stats['total_answers'] * 100) if question_stats['total_answers'] > 0 else 0
                choice_stats.append({
                    'choice': choice,
                    'count': count,
                    'percentage': round(percentage, 1)
                })
            question_stats['choice_stats'] = choice_stats
        else:
            # Для текстовых ответов
            text_answers = SurveyAnswer.objects.filter(
                question=question
            ).exclude(text_answer__isnull=True).exclude(text_answer='')
            question_stats['text_answers_count'] = text_answers.count()

            # Для фото вопросов - добавляем список ответов с фото
            if question.question_type == 'PHOTO':
                question_stats['answers_with_photos'] = SurveyAnswer.objects.filter(
                    question=question
                ).prefetch_related('photos')

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


@csrf_exempt
def getGroupedAnswers(request):
    """
    Return grouped survey answers with filtering and read status.

    Groups answers by task, client, user and date, and includes
    information about whether the group has been marked as read.

    Parameters
    ----------
    request : HttpRequest
        The HTTP request object with optional filter parameters

    Returns
    -------
    JsonResponse
        JSON response containing grouped answers with metadata
        including read status, user who read it, and timestamp

    Notes
    -----
    Supports filtering by task_id, user_id, client_id, and client_search.
    Includes 'isRead', 'readAt', and 'readBy' fields in the response.
    """
    from django.utils import timezone
    from django.db.models import Prefetch
    from datetime import timedelta
    from clients.models import Client

    # Get filters from query parameters
    task_id = request.GET.get('taskId') or request.GET.get('task')
    task_search = request.GET.get('task_search', '').strip()
    task_type = request.GET.get('task_type', '').strip()
    user_id = request.GET.get('userId')
    client_id = request.GET.get('clientId') or request.GET.get('client')
    client_search = request.GET.get('client_search', '').strip()

    # Calculate 24 hours ago for "new" flag
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)

    # Build base queryset
    answers = SurveyAnswer.objects.select_related(
        'user', 'question__task', 'client'
    ).prefetch_related(
        'selected_choices',
        'photos',
        'question__task__created_by'
    ).order_by('-created_at')

    # Apply filters
    if task_id:
        answers = answers.filter(question__task_id=task_id)
    elif task_search:
        # Use case-insensitive search for task title
        answers = answers.filter(question__task__title__icontains=task_search)
    if task_type:
        answers = answers.filter(question__task__task_type=task_type)
    if user_id:
        answers = answers.filter(user_id=user_id)
    if client_id:
        answers = answers.filter(client_id=client_id)
    elif client_search:
        # Use case-insensitive search for client name
        answers = answers.filter(client__name__icontains=client_search)
    if request.GET.get('moderatorId'):
        answers = answers.filter(
            question__task__created_by_id=request.GET.get('moderatorId'))

    # Apply date filters
    date_filter = request.GET.get('date_filter')
    if date_filter:
        from datetime import timedelta
        today = timezone.now().date()
        if date_filter == 'today':
            answers = answers.filter(created_at__date=today)
        elif date_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            answers = answers.filter(created_at__date=yesterday)
        elif date_filter == 'week':
            week_ago = today - timedelta(days=7)
            answers = answers.filter(created_at__date__gte=week_ago)

    # Apply date range filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        answers = answers.filter(created_at__date__gte=date_from)
    if date_to:
        answers = answers.filter(created_at__date__lte=date_to)

    # Group answers by task, client, and user
    grouped_data = {}
    for answer in answers:
        # Convert to local time to get correct date
        from django.utils import timezone
        local_created_at = timezone.localtime(answer.created_at)
        key = f"{answer.question.task.id}_{answer.client.id}_{
            answer.user.id}_{local_created_at.date()}"

        if key not in grouped_data:
            # Check if this group has been marked as read
            from .models import SurveyAnswerGroupReadStatus
            try:
                # Use local date for lookup
                read_status = SurveyAnswerGroupReadStatus.objects.select_related('read_by').get(
                    task=answer.question.task,
                    client=answer.client,
                    user=answer.user,
                    date_created=local_created_at.date()
                )
                is_read = read_status.read_at is not None
                if read_status.read_at:
                    # Convert to Krasnoyarsk time
                    import pytz
                    krasnoyarsk_tz = pytz.timezone('Asia/Krasnoyarsk')
                    read_at_krsk = read_status.read_at.astimezone(
                        krasnoyarsk_tz)
                    read_at = read_at_krsk.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    read_at = None
                read_by = read_status.read_by.get_full_name(
                ) or read_status.read_by.username if read_status.read_by else None
            except SurveyAnswerGroupReadStatus.DoesNotExist:
                is_read = False
                read_at = None
                read_by = None

            grouped_data[key] = {
                'id': key,
                'taskName': answer.question.task.title,
                'clientName': answer.client.name,
                'userName': answer.user.get_full_name() or answer.user.username,
                'dateCreated': answer.created_at,
                'moderatorName': answer.question.task.created_by.get_full_name() or answer.question.task.created_by.username if answer.question.task.created_by else '-',
                'answers': [],
                'isNew': answer.created_at > twenty_four_hours_ago and not is_read,
                'isRead': is_read,
                'readAt': read_at,
                'readBy': read_by,
            }

        # Add answer details
        answer_details = {
            'question': answer.question.question_text,
            'questionType': answer.question.get_question_type_display(),
            'selectedChoices': [choice.choice_text for choice in answer.selected_choices.all()],
            'textAnswer': answer.text_answer,
            'photos': [{'id': photo.id, 'url': photo.photo.url, 'name': photo.photo.name.split('/')[-1]} for photo in answer.photos.all()],
            'createdAt': answer.created_at,
            'questionId': answer.question.id
        }
        grouped_data[key]['answers'].append(answer_details)

    # Convert to list and sort by date created (newest first)
    result = list(grouped_data.values())
    result.sort(key=lambda x: x['dateCreated'], reverse=True)

    # Format dates to string for JSON serialization
    for item in result:
        item['dateCreated'] = item['dateCreated'].strftime('%Y-%m-%d %H:%M:%S')
        for answer in item['answers']:
            answer['createdAt'] = answer['createdAt'].strftime(
                '%Y-%m-%d %H:%M:%S')

    return JsonResponse({'results': result})


@csrf_exempt
def markAsRead(request, answer_id=None):
    """
    Mark a group of survey answers as read by the current user.

    This endpoint handles the marking of survey answer groups as processed
    by storing the user who read it and the timestamp in the database.

    Parameters
    ----------
    request : HttpRequest
        The HTTP request object containing the answer ID
    answer_id : str, optional
        The ID of the answer group in format 'task_client_user_date'
        If not provided, it will be extracted from request body

    Returns
    -------
    JsonResponse
        JSON response with success status and read information
        or error message if operation fails

    Notes
    -----
    The answer_id format is: {task_id}_{client_id}_{user_id}_{YYYY-MM-DD}
    This function handles database constraints gracefully for SQLite compatibility.
    """
    from django.utils import timezone
    from datetime import datetime
    from .models import SurveyAnswerGroupReadStatus

    if request.method == 'POST':
        # Parse the answer_id which contains task_id_client_id_user_id_date
        if answer_id is None:
            # For the new API, we'll use POST data
            try:
                data = json.loads(request.body)
                answer_id = data.get('answerId', '')
            except:
                return JsonResponse({'error': 'Invalid data'}, status=400)

        if answer_id:
            try:
                parts = answer_id.split('_')
                if len(parts) >= 4:
                    task_id = parts[0]
                    client_id = parts[1]
                    user_id = parts[2]
                    # This might be date part from a longer string
                    date_str = parts[3]

                    # Debug output
                    print(f"DEBUG markAsRead: task_id={task_id}, client_id={
                          client_id}, user_id={user_id}, date_str={date_str}")

                    # Convert IDs to integers
                    try:
                        task_id = int(task_id)
                        client_id = int(client_id)
                        user_id = int(user_id)
                    except ValueError as e:
                        print(f"DEBUG markAsRead: ID conversion error: {e}")
                        return JsonResponse({'error': 'Invalid ID format'}, status=400)

                    # Extract only the date part (YYYY-MM-DD) from date_str
                    # The date_str might be just a date, or a datetime with space or 'T' separator
                    date_part = date_str.split('T')[0].split(' ')[0]

                    # Validate date format
                    try:
                        parsed_date = datetime.strptime(
                            date_part, '%Y-%m-%d').date()
                    except ValueError:
                        print(f"DEBUG markAsRead: Invalid date format: {
                              date_part}")
                        return JsonResponse({'error': f'Invalid date format: {date_part}'}, status=400)

                    # Debug output after parsing
                    print(f"DEBUG markAsRead: parsed - task_id={task_id}, client_id={
                          client_id}, user_id={user_id}, date={parsed_date}")

                    # Fallback: direct database operation with error handling
                    from django.db import connection

                    try:
                        current_user = request.user if request.user.is_authenticated else None
                        current_time = timezone.now()

                        # First, try to update existing record
                        updated = SurveyAnswerGroupReadStatus.objects.filter(
                            task_id=task_id,
                            client_id=client_id,
                            user_id=user_id,
                            date_created=parsed_date
                        ).update(
                            read_at=current_time,
                            read_by=current_user
                        )

                        if updated > 0:
                            read_status = SurveyAnswerGroupReadStatus.objects.get(
                                task_id=task_id,
                                client_id=client_id,
                                user_id=user_id,
                                date_created=parsed_date
                            )
                            created = False
                        else:
                            # No existing record, create new one
                            read_status = SurveyAnswerGroupReadStatus.objects.create(
                                task_id=task_id,
                                client_id=client_id,
                                user_id=user_id,
                                date_created=parsed_date,
                                read_at=current_time,
                                read_by=current_user
                            )
                            created = True

                    except Exception:
                        # Final fallback: use raw SQL (for SQLite compatibility)
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    INSERT INTO tasks_surveyanswergroupreadstatus
                                    (task_id, client_id, user_id, date_created,
                                     read_at, read_by_id, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT(task_id, client_id, user_id, date_created)
                                    DO UPDATE SET read_at = %s, read_by_id = %s, created_at = %s
                                """, [
                                    task_id, client_id, user_id, parsed_date,
                                    timezone.now(),
                                    request.user.id if request.user.is_authenticated else None,
                                    timezone.now(),
                                    timezone.now(),
                                    request.user.id if request.user.is_authenticated else None,
                                    timezone.now()
                                ])

                            read_status = SurveyAnswerGroupReadStatus.objects.get(
                                task_id=task_id,
                                client_id=client_id,
                                user_id=user_id,
                                date_created=parsed_date
                            )
                            created = False

                        except Exception:
                            return JsonResponse({'error': 'Database operation failed'}, status=500)

                    # Convert to Krasnoyarsk time for display
                    from django.utils import timezone
                    import pytz
                    krasnoyarsk_tz = pytz.timezone('Asia/Krasnoyarsk')
                    read_at_krsk = read_status.read_at.astimezone(
                        krasnoyarsk_tz)

                    return JsonResponse({
                        'success': True,
                        'readAt': read_at_krsk.strftime('%Y-%m-%d %H:%M:%S'),
                        'readBy': read_status.read_by.get_full_name() or read_status.read_by.username if read_status.read_by else 'Неизвестно',
                        'message': 'Статус прочтения обновлен'
                    })
                else:
                    return JsonResponse({'error': 'Invalid answer ID format'}, status=400)
            except SurveyAnswerGroupReadStatus.DoesNotExist:
                return JsonResponse({'error': 'Read status does not exist'}, status=404)
            except Exception as e:
                # Log the actual error for debugging
                print(f"markAsRead error: {str(e)}")
                return JsonResponse({'error': 'Internal server error'}, status=500)
        else:
            return JsonResponse({'error': 'Answer ID is required'}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def search_clients(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '').strip()

        if len(query) < 2:
            return JsonResponse({'error': 'Введите минимум 2 символа для поиска'}, status=400)

        # Use database indexing for faster search
        clients = Client.objects.filter(
            name__icontains=query
        ).order_by('name')[:20]

        if len(clients) == 0:
            return JsonResponse({'message': 'Клиенти не найдены'})

        client_list = [{'id': client.id, 'name': client.name}
                       for client in clients]

        if len(clients) == 20:
            return JsonResponse({
                'clients': client_list,
                'message': 'Найдено 20 совпадений. Уточните запрос для более точного результата.'
            })
        else:
            return JsonResponse({'clients': client_list})

    return JsonResponse({'error': 'Метод не поддерживается'}, status=400)


def autocomplete_clients(request):
    """
    API endpoint for client autocomplete.

    This is a proxy to the dedicated clients autocomplete view.
    Redirects to /clients/autocomplete/ for reusable logic.
    """
    from django.shortcuts import redirect
    from django.http import QueryDict

    # Build the redirect URL with the query parameters
    query = request.GET.get('q', '')
    redirect_url = "/clients/autocomplete/"
    if query:
        redirect_url += f"?q={query}"

    return redirect(redirect_url)


def autocomplete_tasks(request):
    """API endpoint for task autocomplete functionality with case-insensitive search."""
    query = request.GET.get('q', '').strip()

    if len(query) < 1:
        return JsonResponse({'tasks': []})

    # Fallback to Python-side case-insensitive search for Cyrillic
    query_lower = query.lower()
    all_tasks = Task.objects.all().order_by('title')

    tasks = []
    for task in all_tasks:
        if query_lower in task.title.lower():
            tasks.append({
                'id': task.id,
                'title': task.title
            })
            if len(tasks) >= 20:
                break

    return JsonResponse({'tasks': tasks})


def equipment_photo_reports_view(request):
    """View for equipment photo reports page."""
    from clients.models import Client
    from users.models import CustomUser
    from .models import Task
    from datetime import timedelta

    # Get all equipment photo tasks
    equipment_tasks = Task.objects.filter(task_type=TaskType.EQUIPMENT_PHOTO)
    clients = Client.objects.all()
    users = CustomUser.objects.filter(role='EMPLOYEE')

    context = {
        'title': 'Фотоотчеты по оборудованию',
        'tasks': equipment_tasks,
        'clients': clients,
        'users': users,
        'opts': Task._meta,  # Using Task model meta for admin interface
        'current_date': timezone.now(),
        'previous_date': timezone.now() - timedelta(days=1),
    }

    return render(request, 'admin/tasks/equipment_photo_reports.html', context)


@csrf_exempt
def equipment_photo_reports_api(request):
    """API endpoint to return equipment photo reports with filtering."""
    from django.utils import timezone
    from .models import PhotoReport, PhotoReportItem
    import logging
    logger = logging.getLogger(__name__)

    # Get filters from query parameters
    task_id = request.GET.get('task_id')
    user_id = request.GET.get('user_id')
    client_id = request.GET.get('client_id')
    client_search = request.GET.get('client_search', '').strip()
    task_search = request.GET.get('task_search', '').strip()

    logger.debug(f"equipment_photo_reports_api called with filters: task_id={task_id}, user_id={
                 user_id}, client_id={client_id}, client_search={client_search}, task_search={task_search}")

    # Build base queryset for equipment photo reports
    reports = PhotoReport.objects.filter(
        task__task_type=TaskType.EQUIPMENT_PHOTO
    ).select_related(
        'task', 'client', 'created_by'
    ).prefetch_related(
        'photos'
    ).order_by('-created_at')

    logger.debug(f"Initial queryset count: {reports.count()}")

    # Apply filters
    if task_id:
        reports = reports.filter(task_id=task_id)
    if user_id:
        reports = reports.filter(created_by_id=user_id)
    if client_id:
        reports = reports.filter(client_id=client_id)
    if client_search:
        reports = reports.filter(client__name__icontains=client_search)
    if task_search:
        reports = reports.filter(task__title__icontains=task_search)

    logger.debug(f"Filtered queryset count: {reports.count()}")

    # Convert to the expected format
    results = []
    for report in reports:
        try:
            # Принудительно обновляем задачу из базы данных для актуального статуса
            report.task.refresh_from_db()
            report_data = {
                'id': f"{report.id}",
                'taskName': report.task.title,
                'clientName': report.client.name,
                'userName': report.created_by.get_full_name() or report.created_by.username or report.created_by.email,
                'dateCreated': report.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'status': report.task.status,
                'averageRating': report.get_average_rating(),
                # Оценки по категориям
                'equipmentFill': report.equipment_fill,
                'noForeignGoods': report.no_foreign_goods,
                'productDisplay': report.product_display,
                'equipmentLocation': report.equipment_location,
                # Модерация
                'moderated': report.moderated_at is not None,
                'moderatorName': str(report.moderated_by) if report.moderated_by else None,
                'moderatedAt': report.moderated_at.strftime('%Y-%m-%d %H:%M:%S') if report.moderated_at else None,
                # Комментарий и адрес
                'moderatorComment': getattr(report.task, 'moderator_comment', ''),
                'personalComment': report.comment,
                'clientAddress': report.address,
                'isFresh': report.is_fresh(),  # Для подсветки "свежих" отчётов
                'photos': [],
                # Количество стендов
                'reportedStandCount': report.stand_count,
                'taskStandCount': getattr(report.task, 'stand_count', 0),
                'clientStandCount': getattr(report.client, 'stand_count', 0),
                'clientId': report.client.id,
                'taskId': report.task.id,
                'reportId': report.id,
            }

            # Add photos with geolocation data
            for photo in report.photos.all():
                # Include metadata for proper display
                author_name = report.created_by.get_full_name() or report.created_by.username or report.created_by.email
                
                photo_data = {
                    'id': photo.id,
                    'url': photo.photo.url,
                    'name': photo.photo.name.split('/')[-1],
                    # Use stored geolocation data
                    'latitude': float(photo.latitude) if photo.latitude else None,
                    'longitude': float(photo.longitude) if photo.longitude else None,
                    'location_address': photo.location_address,
                    # Include metadata for proper display
                    'author': author_name,
                    'dateCreated': report.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'address': report.address,
                }

                # Extract EXIF date if available (for backward compatibility)
                try:
                    from PIL import Image
                    from PIL.ExifTags import TAGS
                    if photo.photo and hasattr(photo.photo, 'path'):
                        img = Image.open(photo.photo.path)
                        exifdata = img.getexif()
                        if exifdata:
                            exif_dict = {}
                            for tag_id in exifdata:
                                tag = TAGS.get(tag_id, tag_id)
                                data = exifdata.get(tag_id)
                                if isinstance(data, bytes):
                                    try:
                                        data = data.decode()
                                    except:
                                        data = str(data)
                                exif_dict[tag] = data

                            # Extract date from EXIF
                            exif_date = None
                            for date_tag in ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']:
                                if date_tag in exif_dict:
                                    exif_date = exif_dict[date_tag]
                                    break

                            photo_data['exif_date'] = exif_date
                except Exception as e:
                    print(f"Error extracting EXIF data for photo {
                          photo.id}: {e}")

                report_data['photos'].append(photo_data)

            results.append(report_data)
        except Exception as e:
            logger.error(f"Error processing report {
                         report.id}: {str(e)}", exc_info=True)
            continue

    logger.debug(f"Final results count: {len(results)}")
    return JsonResponse({'results': results})


def reverse_geocode(latitude, longitude):
    """
    Преобразует координаты в читаемый адрес с использованием Nominatim API.
    Возвращает строку с адресом или None в случае ошибки.
    """
    try:
        import requests
        import time
        
        # Используем OpenStreetMap Nominatim API (бесплатный, но с ограничениями)
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'format': 'json',
            'lat': latitude,
            'lon': longitude,
            'accept-language': 'ru',  # Русский язык для адр��сов
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'microCRM/1.0 (contact@example.com)'  # Требуется для Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'display_name' in data:
                # Ограничиваем длину адреса для удобства отображения
                address = data['display_name']
                if len(address) > 100:
                    address = address[:97] + "..."
                return address
        return None
    except Exception as e:
        print(f"Error in reverse geocoding: {e}")
        return None


# Equipment Photo Reports API View
@login_required
@require_http_methods(["GET"])
def equipment_photo_reports_api_view(request):
    """Django view wrapper for the API endpoint."""
    return equipment_photo_reports_api(request)


# Save Personal Comment API
@login_required
@require_http_methods(["POST"])
def save_personal_comment(request):
    """
    Сохраняет личную заметку модератора к фотоотчёту.

    Принимает JSON: {"report_id": 123, "comment": "Текст заметки"}
    """
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        comment = data.get('comment', '')

        if not report_id:
            return JsonResponse({'error': 'Отсутствует report_id'}, status=400)

        # Проверка роли: только модератор
        if not hasattr(request.user, 'role') or request.user.role != 'MODERATOR':
            return JsonResponse({'error': 'Только модератор может сохранять заметки'}, status=403)

        report = PhotoReport.objects.get(id=report_id)
        report.comment = comment
        report.save(update_fields=['comment'])

        return JsonResponse({'success': True, 'message': 'Заметка сохранена'})

    except PhotoReport.DoesNotExist:
        return JsonResponse({'error': 'Фотоотчёт не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Оши��ка: {str(e)}'}, status=500)

# Send Photo Report to Rework API


@login_required
@require_http_methods(["POST"])
def send_photo_report_to_rework(request):
    """
    Отправляет фотоотчёт на доработку.

    Принимает JSON: {"report_id": 123, "comment": "Комментарий для сотрудника"}
    Обновляет статус задачи на REWORK и активирует её.
    """
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        comment = data.get('comment', '').strip()
        if not report_id:
            return JsonResponse({'error': 'Отсутствует report_id'}, status=400)
        if not comment:
            return JsonResponse({'error': 'Комментарий не может быть пустым'}, status=400)

        # Проверка роли: только модератор
        if not hasattr(request.user, 'role') or request.user.role != 'MODERATOR':
            return JsonResponse({'error': 'Только модератор может отправлять на доработку'}, status=403)

        report = PhotoReport.objects.get(id=report_id)
        task = report.task

        # Обно��ляем комментарий модератора и статус
        task.moderator_comment = comment
        task.status = TaskStatus.REWORK
        task.is_active = True  # Активируем задачу для сотрудника
        task.save(update_fields=['moderator_comment', 'status', 'is_active'])

        return JsonResponse({
            'success': True,
            'message': 'Отчёт ��тправлен на доработку',
            'status': 'REWORK'
        })

    except PhotoReport.DoesNotExist:
        return JsonResponse({'error': 'Фотоотчёт не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Ошибка: {str(e)}'}, status=500)

# Process Equipment Photo Report API


@login_required
@require_http_methods(["POST"])
def process_equipment_photo_report(request):
    """
    Обрабатывает фотоотчёт модератором.
    Принимает JSON:
    {
        "report_id": 123,
        "equipment_fill": 3,
        "no_foreign_goods": 2,
        "product_display": 3,
        "equipment_location": 1
    }
    Требует, чтобы пользователь был модератором.
    Сохраняет оценки и устанавливает moderated_by и moderated_at.

    ВАЖНО: Эта функция обновляет статус ТОЛЬКО конкретной задачи, связанной с указанным отчётом.
    Статус задачи меняется на ACCEPTED только при явном нажатии кнопки "Принять".
    """
    from django.utils import timezone
    import logging
    logger = logging.getLogger(__name__)
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        if not report_id:
            return JsonResponse({'error': 'Отсутствует report_id'}, status=400)
        # Проверка роли: только модератор
        if not hasattr(request.user, 'role') or request.user.role != 'MODERATOR':
            return JsonResponse({'error': 'Только модератор может обрабатывать отчёты'}, status=403)
        report = PhotoReport.objects.select_related('task').get(id=report_id)
        task = report.task

        # Отладочный лог
        logger.info(f"DEBUG process_equipment_photo_report: report_id={
                    report_id}, task_id={task.id}, current_task_status={task.status}")

        # Уже обработан?
        if report.moderated_at:
            logger.info(f"DEBUG: Отчёт {report_id} уже обработан")
            return JsonResponse({'warning': 'Отчёт уже обработан'}, status=200)
        # Валидация и сохранение оценок
        rating_fields = [
            'equipment_fill',
            'no_foreign_goods',
            'product_display',
            'equipment_location'
        ]
        for field in rating_fields:
            value = data.get(field)
            if value is None:
                return JsonResponse({'error': f'Отсутствует оценка: {field}'}, status=400)
            if value not in [1, 2, 3]:
                return JsonResponse({'error': f'Некорректное значение для {field}: {value}'}, status=400)
            setattr(report, field, value)
        # Обновляем модерацию
        report.moderated_by = request.user
        report.moderated_at = timezone.now()
        report.save(update_fields=rating_fields +
                    ['moderated_by', 'moderated_at'])

        # Обновляем статус ТОЛЬКО этой конкретной задачи
        logger.info(f"DEBUG: Обновление статуса задачи {
                    task.id} на {TaskStatus.ON_CHECK}")
        task.status = TaskStatus.ON_CHECK
        task.save(update_fields=['status'])

        logger.info(f"DEBUG: Возвращаем ответ для report_id={
                    report_id}, average_rating={report.get_average_rating()}")
        return JsonResponse({
            'success': True,
            'message': f'Отчёт обработан модератором {request.user.get_full_name() or request.user.username}',
            'moderated_at': report.moderated_at.isoformat(),
            'moderator_name': str(request.user),
            'average_rating': report.get_average_rating()
        })
    except PhotoReport.DoesNotExist:
        logger.error(f"DEBUG: Фотоотчёт не найден, report_id={report_id}")
        return JsonResponse({'error': 'Фотоотчёт не найден'}, status=404)
    except Exception as e:
        logger.error(f"DEBUG: Ошибка в process_equipment_photo_report: {
                     str(e)}", exc_info=True)
        return JsonResponse({'error': f'Ошибка: {str(e)}'}, status=500)

# Accept Equipment Photo Report API


@login_required
@require_http_methods(["POST"])
def accept_equipment_photo_report(request):
    """
    Принимает фотоотчёт как корректный.

    Принимает JSON: {"report_id": 123}
    Обновляет статус ТОЛЬКО конкретной задачи, связанной с указанным отчётом.
    """
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        if not report_id:
            return JsonResponse({'error': 'Отсутствует report_id'}, status=400)

        # Проверка роли: только модератор
        if not hasattr(request.user, 'role') or request.user.role != 'MODERATOR':
            return JsonResponse({'error': 'Только модератор может принимать отчёты'}, status=403)

        report = PhotoReport.objects.select_related('task').get(id=report_id)
        task = report.task

        # Обновляем статус ТОЛЬКО этой конкретной задачи
        task.status = TaskStatus.ACCEPTED
        task.is_active = False  # Задача завершена
        task.save(update_fields=['status', 'is_active'])

        return JsonResponse({
            'success': True,
            'message': f'Отчёт принят модератором {request.user.get_full_name() or request.user.username}'
        })

    except PhotoReport.DoesNotExist:
        return JsonResponse({'error': 'Фотоотчёт не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Ошибка: {str(e)}'}, status=500)


# Employee Group API
@login_required
@user_passes_test(lambda u: u.role == 'MODERATOR')
def get_employee_group_employees(request, group_id):
    """API endpoint to get employees in a specific employee group."""
    try:
        group = EmployeeGroup.objects.get(id=group_id)
        employees = group.customuser_set.filter(role='EMPLOYEE').values(
            'id', 'username', 'first_name', 'last_name')
        employee_list = []
        for emp in employees:
            name = f"{emp['first_name']} {emp['last_name']}".strip()
            if not name:
                name = emp['username']
            employee_list.append({
                'id': emp['id'],
                'name': name
            })
        return JsonResponse({'employees': employee_list})
    except EmployeeGroup.DoesNotExist:
        return JsonResponse({'error': 'Employee group not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Client Group API
@login_required
@user_passes_test(lambda u: u.role == 'MODERATOR')
def get_client_group_clients(request, group_id):
    """API endpoint to get clients in a specific client group."""
    try:
        group = ClientGroup.objects.get(id=group_id)
        clients = group.client_set.values('id', 'name')
        client_list = [{'id': c['id'], 'name': c['name']} for c in clients]
        return JsonResponse({'clients': client_list})
    except ClientGroup.DoesNotExist:
        return JsonResponse({'error': 'Client group not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Update Client Stand Count API
@login_required
@require_http_methods(["POST"])
@user_passes_test(lambda u: u.role == 'MODERATOR')
def update_client_stand_count(request):
    """Обновляет количество стендов у клиента."""
    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
        new_count = data.get('stand_count')

        if not client_id or new_count is None:
            return JsonResponse({'error': 'Недостаточно данных'}, status=400)

        client = Client.objects.get(id=client_id)
        client.stand_count = int(new_count)
        client.save(update_fields=['stand_count'])

        return JsonResponse({'success': True, 'message': 'Количество стендов обновлено'})
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Клиент не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Get Submitted Clients API
@login_required
@user_passes_test(lambda u: u.role == 'MODERATOR')
def get_submitted_clients(request, task_id):
    """API endpoint to get list of clients who have submitted reports for a task."""
    from .models import PhotoReport
    submitted_client_ids = list(
        PhotoReport.objects.filter(
            task_id=task_id).values_list('client_id', flat=True)
    )
    return JsonResponse({'submitted_client_ids': submitted_client_ids})


# Views for Daily Task Widget
@login_required
def daily_task_widget_view(request):
    """Display the daily task widget for employees."""
    from .models import DailyTask, Task, TaskStatus
    from clients.models import Client
    from users.models import CustomUser
    from django.db.models import Q

    # Get today's date for default filtering
    from datetime import date
    today = date.today()

    # Get daily tasks for the current user (both as creator and assignee)
    # Remove the date filter to show all tasks for filtering in JS
    daily_tasks = DailyTask.objects.filter(
        Q(creator=request.user) | Q(assignee=request.user)
    ).order_by('position', '-created_at')

    # Get all clients for the dropdown
    clients = Client.objects.all()

    # Get all employees for the assignee dropdown
    employees = CustomUser.objects.filter(role='EMPLOYEE')

    # Get active clients for tasks that might match daily tasks
    active_tasks = Task.objects.filter(
        status__in=[TaskStatus.SENT, TaskStatus.REWORK],
        is_active=True
    ).filter(
        Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
    )

    # Build a dictionary with client info: {client_id: {'count': N, 'types': set()}}
    active_clients_data = {}
    for task_obj in active_tasks:
        client_id = None
        # First check direct client field
        if task_obj.client_id:
            client_id = task_obj.client_id
        # Also check task client assignments
        else:
            assignments = task_obj.taskclientassignment_set.all()
            if assignments:
                client_id = assignments[0].client_id
        
        if client_id:
            if client_id not in active_clients_data:
                active_clients_data[client_id] = {'count': 0, 'types': set()}
            active_clients_data[client_id]['count'] += 1
            active_clients_data[client_id]['types'].add(task_obj.task_type)

    # Get active clients queryset
    active_client_ids = set(active_clients_data.keys())
    active_clients = Client.objects.filter(id__in=active_client_ids)
    
    # Add extra data to each client object
    for client in active_clients:
        if client.id in active_clients_data:
            client.tasks_count = active_clients_data[client.id]['count']
            client.tasks_types = active_clients_data[client.id]['types']
        else:
            client.tasks_count = 1
            client.tasks_types = set()

    # Debug: print active clients data
    print(f"[DEBUG] active_clients_data: {active_clients_data}")
    for client in active_clients:
        print(f"[DEBUG] Client {client.name}: tasks_count={client.tasks_count}, tasks_types={client.tasks_types}")

    context = {
        'daily_tasks': daily_tasks,
        'clients': clients,
        'employees': employees,
        'today': today,
        'active_clients': active_clients,
    }

    return render(request, 'tasks/daily_task_widget.html', context)


@login_required
def create_daily_task(request):
    """Create a new daily task."""
    from .models import DailyTask
    from clients.models import Client
    from users.models import CustomUser
    from django.http import JsonResponse
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            date_str = data.get('date')
            client_id = data.get('client_id')
            assignee_id = data.get('assignee_id')
            description = data.get('description')
            priority = data.get('priority', 3)
            
            # Validate required fields
            if not date_str or not client_id or not description:
                return JsonResponse({'error': 'Не все обязательные поля заполнены'}, status=400)
            
            # Parse date
            from datetime import datetime
            task_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Get related objects
            # Check if client_id is numeric (ID) or string (name)
            try:
                client_id_int = int(client_id)
                client = Client.objects.get(id=client_id_int)
            except ValueError:
                # If it's not a number, treat it as a name
                client = Client.objects.get(name=client_id)
            
            assignee = CustomUser.objects.get(id=assignee_id) if assignee_id else request.user
            
            # Check for duplicate task to prevent duplicates
            existing_task = DailyTask.objects.filter(
                date=task_date,
                client=client,
                assignee=assignee,
                creator=request.user,
                description=description
            ).first()
            
            if existing_task:
                return JsonResponse({
                    'success': False,
                    'error': 'Задача с такими параметрами уже существует'
                })

            # Create the daily task
            daily_task = DailyTask.objects.create(
                date=task_date,
                client=client,
                assignee=assignee,
                creator=request.user,
                description=description,
                priority=priority
            )
            
            return JsonResponse({
                'success': True,
                'task_id': daily_task.id,
                'message': 'Задача успешно создана'
            })
            
        except Client.DoesNotExist:
            return JsonResponse({'error': 'Клиент не найден'}, status=400)
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'Исполнитель не найден'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def update_daily_task(request, task_id):
    """Update an existing daily task."""
    from .models import DailyTask
    from clients.models import Client
    from users.models import CustomUser
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            daily_task = get_object_or_404(DailyTask, id=task_id)
            
            # Check if user has permission to edit this task
            if request.user != daily_task.creator and request.user != daily_task.assignee and request.user.role != 'MODERATOR':
                return JsonResponse({'error': 'Нет прав для редактирования задачи'}, status=403)
            
            # Update fields if provided
            if 'date' in data:
                from datetime import datetime
                daily_task.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            
            if 'client_id' in data:
                # Check if client_id is numeric (ID) or string (name)
                try:
                    client_id = int(data['client_id'])
                    client = Client.objects.get(id=client_id)
                except ValueError:
                    # If it's not a number, treat it as a name
                    client = Client.objects.get(name=data['client_id'])
                daily_task.client = client
            
            if 'assignee_id' in data and data['assignee_id']:
                assignee = CustomUser.objects.get(id=data['assignee_id'])
                daily_task.assignee = assignee
            else:
                # If no assignee_id provided or it's empty, keep the current assignee
                if not daily_task.assignee_id:
                    daily_task.assignee = request.user
            
            if 'description' in data:
                daily_task.description = data['description']
            
            if 'result' in data:
                daily_task.result = data['result']
                
            if 'status' in data:
                daily_task.status = data['status']
                
            if 'priority' in data:
                daily_task.priority = data['priority']
                
            if 'position' in data:
                daily_task.position = data['position']
            
            daily_task.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Задача успешно обновлена'
            })
            
        except Client.DoesNotExist:
            return JsonResponse({'error': 'Клиент не найден'}, status=400)
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'Исполнитель не найден'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def delete_daily_task(request, task_id):
    """Delete a daily task."""
    from .models import DailyTask
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    
    if request.method == 'POST':
        try:
            daily_task = get_object_or_404(DailyTask, id=task_id)
            
            # Check if user has permission to delete this task
            if request.user != daily_task.creator and request.user.role != 'MODERATOR':
                return JsonResponse({'error': 'Нет прав для удаления задачи'}, status=403)
            
            daily_task.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Задача успешно удалена'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def toggle_daily_task_status(request, task_id):
    """Toggle the status of a daily task (active/completed)."""
    from .models import DailyTask
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    
    if request.method == 'POST':
        try:
            daily_task = get_object_or_404(DailyTask, id=task_id)
            
            # Check if user has permission to update this task
            if request.user != daily_task.assignee and request.user.role != 'MODERATOR':
                return JsonResponse({'error': 'Нет прав для обновления статуса задачи'}, status=403)
            
            # Toggle status between active and completed
            if daily_task.status == 'active':
                daily_task.status = 'completed'
            elif daily_task.status == 'completed':
                daily_task.status = 'active'
            else:
                # For hidden tasks, make them active
                daily_task.status = 'active'
            
            daily_task.save()
            
            return JsonResponse({
                'success': True,
                'status': daily_task.status,
                'message': 'Статус задачи успешно обновлен'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def update_task_positions(request):
    """Update positions of daily tasks for sorting."""
    from .models import DailyTask
    from django.http import JsonResponse
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_positions = data.get('positions', [])
            
            for position, task_id in enumerate(task_positions):
                task = DailyTask.objects.get(id=task_id)
                # Only allow updating position if user is the creator or a moderator
                if request.user == task.creator or request.user.role == 'MODERATOR':
                    task.position = position
                    task.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Позиции задач успешно обновлены'
            })
            
        except DailyTask.DoesNotExist:
            return JsonResponse({'error': 'Одна из задач не найдена'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


@login_required
def hide_daily_task(request, task_id):
    """Hide a daily task (only for creators)."""
    from .models import DailyTask
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    
    if request.method == 'POST':
        try:
            daily_task = get_object_or_404(DailyTask, id=task_id)
            
            # Only the creator can hide the task
            if request.user != daily_task.creator:
                return JsonResponse({'error': 'Только создатель может скрыть задачу'}, status=403)
            
            daily_task.status = 'hidden'
            daily_task.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Задача успешно скрыта'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)
