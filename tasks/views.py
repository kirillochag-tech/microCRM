# -*- coding: utf-8 -*-
"""
Task management views.

This module provides views for displaying and managing tasks.
Follows SOLID principles by separating concerns and providing clear interfaces.
"""
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from .forms import SurveyResponseForm, AddPhotosForm, AddSinglePhotoForm
from .models import Task, TaskStatus, TaskType
from users.models import CustomUser
from .models import SurveyAnswer, SurveyQuestion, SurveyAnswerPhoto
from clients.models import Client

from django.db.models import Count, Sum, Avg, Q
from django.http import JsonResponse
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
            return Task.objects.filter(
                status__in=[TaskStatus.SENT, TaskStatus.REWORK, TaskStatus.ON_CHECK],
                is_active=True
            ).filter(
                Q(assigned_to=user) | Q(assigned_to__isnull=True)
            ).order_by('-created_at')
        elif user.role == 'MODERATOR':
            return Task.objects.all().order_by('-created_at')
        return Task.objects.none()
    
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
        
        user = self.request.user
        context['debug_info'] = {
            'user_role': user.role,
            'task_status': context['task'].status,
            'task_is_completed': context['task'].status == 'COMPLETED',
            'user_can_view': context['task'].can_be_viewed_by(user),
            'user_can_edit': context['task'].can_be_edited_by(user),
        }
        
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
        if task.task_type != TaskType.SURVEY:
            raise Http404(_("Задача не является анкетой"))
        kwargs['task'] = task
        kwargs['user'] = self.request.user
        return kwargs
    
    # В SurveyResponseView метод form_valid

    def form_valid(self, form):
        try:
            form.save()
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        
        task = form.task
        
        # Для фотоотчетов — статус "На проверке"
        if task.task_type in [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]:
            task.status = TaskStatus.ON_CHECK
            task.is_active = False  # Фотоотчет становится неактивным после отправки
        
        # Для анкет — увеличиваем счетчик, но остаемся активными
        elif task.task_type == TaskType.SURVEY:
            task.current_count += 1
            # Не меняем статус и активность до тех пор, пока модератор не завершит задачу
            # Проверяем, достигнут ли план - если да, меняем статус на "На проверке", но оставляем активной
            if task.target_count > 0 and task.current_count >= task.target_count:
                if task.status != TaskStatus.COMPLETED:
                    task.status = TaskStatus.ON_CHECK
                # Задача остается активной, чтобы сотрудник мог продолжать заполнять
            
        task.save()
        messages.success(self.request, _("Анкета успешно заполнена!"))
        return redirect('tasks:task_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task_id = self.kwargs['task_id']
        context['task'] = get_object_or_404(Task, id=task_id)
        context['title'] = _('Заполнение анкеты')
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
        context['completed_tasks'] = Task.objects.filter(status='COMPLETED').count()
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
            messages.error(self.request, _("Максимальное количество фото (10) уже достигнуто."))
            return self.form_invalid(form)
        
        # ИСПРАВЛЕНО: используем self.request.FILES вместо self.files
        uploaded_files = self.request.FILES.getlist('photos')
        actual_upload_count = min(len(uploaded_files), remaining_slots)
        
        for i in range(actual_upload_count):
            SurveyAnswerPhoto.objects.create(
                answer=answer,
                photo=uploaded_files[i]
            )
        
        messages.success(self.request, _(f"Успешно добавлено {actual_upload_count} фото."))
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
            messages.error(self.request, _("Максимальное количество фото (10) уже достигнуто."))
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
        context['photo_tasks'] = tasks.filter(task_type__in=['EQUIPMENT_PHOTO', 'SIMPLE_PHOTO']).count()
        
        # Статистика по сотрудникам
        context['employees_stats'] = CustomUser.objects.filter(role='EMPLOYEE').annotate(
            total_tasks=Count('tasks_assigned'),
            completed_tasks=Count('tasks_assigned', filter=Q(tasks_assigned__status='COMPLETED')),
            on_check_tasks=Count('tasks_assigned', filter=Q(tasks_assigned__status='ON_CHECK'))
        ).order_by('-total_tasks')
        
        # Статистика по клиентам
        context['clients_stats'] = Client.objects.annotate(
            total_tasks=Count('tasks'),
            completed_tasks=Count('tasks', filter=Q(tasks__status='COMPLETED')),
            on_check_tasks=Count('tasks', filter=Q(tasks__status='ON_CHECK'))
        ).order_by('-total_tasks')
        
        # Статистика по анкетам
        survey_tasks = tasks.filter(task_type='SURVEY')
        context['survey_statistics'] = []
        
        for task in survey_tasks:
            total_answers = SurveyAnswer.objects.filter(question__task=task).count()
            unique_clients = SurveyAnswer.objects.filter(question__task=task).values('client').distinct().count()
            completion_rate = 0
            
            if task.target_count > 0:
                completion_rate = min(100, int((task.current_count / task.target_count) * 100))
            
            context['survey_statistics'].append({
                'task': task,
                'total_answers': total_answers,
                'unique_clients': unique_clients,
                'completion_rate': completion_rate
            })
        
        # График для первой анкеты
        if context['survey_statistics']:
            first_survey = context['survey_statistics'][0]
            context['first_survey_chart_data'] = self.get_chart_data(first_survey['task'])
        
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
            answers_count = SurveyAnswer.objects.filter(question=question).count()
            data['datasets'][0]['data'].append(answers_count)
        
        return data
    
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
        
        if question.has_custom_choices():
            choice_stats = []
            for choice in question.choices.all():
                count = SurveyAnswer.objects.filter(
                    question=question,
                    selected_choices=choice
                ).count()
                percentage = (count / question_stats['total_answers'] * 100) if question_stats['total_answers'] > 0 else 0
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
    """API endpoint to return grouped survey answers with filtering and new status."""
    from django.utils import timezone
    from django.db.models import Prefetch
    from datetime import timedelta
    from clients.models import Client
    
    # Get filters from query parameters
    task_id = request.GET.get('taskId')
    user_id = request.GET.get('userId')
    client_id = request.GET.get('clientId')
    # Also accept client search parameter for text-based search
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
    if user_id:
        answers = answers.filter(user_id=user_id)
    if client_id:
        answers = answers.filter(client_id=client_id)
    
    # Group answers by task, client, and user
    grouped_data = {}
    for answer in answers:
        key = f"{answer.question.task.id}_{answer.client.id}_{answer.user.id}_{answer.created_at.date()}"
        
        if key not in grouped_data:
            # Check if this group has been marked as read
            from .models import SurveyAnswerGroupReadStatus
            try:
                read_status = SurveyAnswerGroupReadStatus.objects.get(
                    task=answer.question.task,
                    client=answer.client,
                    user=answer.user,
                    date_created=answer.created_at.date()
                )
                is_read = read_status.read_at is not None
                read_at = read_status.read_at.strftime('%Y-%m-%d %H:%M:%S') if read_status.read_at else None
            except SurveyAnswerGroupReadStatus.DoesNotExist:
                is_read = False
                read_at = None
            
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
            answer['createdAt'] = answer['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
    
    return JsonResponse({'results': result})


@csrf_exempt
def markAsRead(request, answer_id=None):
    """API endpoint to mark an answer group as read."""
    from django.utils import timezone
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
                    date_str = parts[3]  # This might be date part from a longer string
                    
                    # Create or update the read status
                    read_status, created = SurveyAnswerGroupReadStatus.objects.get_or_create(
                        task_id=task_id,
                        client_id=client_id,
                        user_id=user_id,
                        date_created=date_str,
                        defaults={
                            'read_at': timezone.now(),
                            'read_by': request.user if request.user.is_authenticated else None
                        }
                    )
                    
                    if not created:
                        # Update the existing record
                        read_status.read_at = timezone.now()
                        read_status.read_by = request.user if request.user.is_authenticated else None
                        read_status.save()
                    
                    return JsonResponse({
                        'success': True, 
                        'readAt': read_status.read_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': 'Статус прочтения обновлен'
                    })
                else:
                    return JsonResponse({'error': 'Invalid answer ID format'}, status=400)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
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

        client_list = [{'id': client.id, 'name': client.name} for client in clients]

        if len(clients) == 20:
            return JsonResponse({
                'clients': client_list,
                'message': 'Найдено 20 совпадений. Уточните запрос для более точного результата.'
            })
        else:
            return JsonResponse({'clients': client_list})

    return JsonResponse({'error': 'Метод не поддерживается'}, status=400)


def autocomplete_clients(request):
    """API endpoint for client autocomplete functionality with case-insensitive search."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'clients': []})
    
    # Case-insensitive search using __icontains
    escaped_query = re.escape(query)
    clients = Client.objects.filter(
            name__iregex=escaped_query
        ).distinct()[:20]
    # clients = Client.objects.filter(
    #     name__icontains=query
    # ).order_by('name')[:10]  # Limit to 10 results as requested
    
    client_list = [{'id': client.id, 'name': client.name} for client in clients]
    
    return JsonResponse({'clients': client_list})
def autocomplete_tasks(request):
    """API endpoint for task autocomplete functionality with case-insensitive search."""
    query = request.GET.get('q', '').strip()

    if len(query) < 1:
        return JsonResponse({'tasks': []})

    # Case-insensitive search using __icontains
    escaped_query = re.escape(query)
    tasks = Task.objects.filter(
            title__iregex=escaped_query
        ).distinct()[:20]

    task_list = [{'id': task.id, 'title': task.title} for task in tasks]

    return JsonResponse({'tasks': task_list})
