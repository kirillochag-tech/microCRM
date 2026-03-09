"""
Authentication and user management views.

This module provides views for user authentication, registration,
and profile management. Follows SOLID principles by separating
authentication logic from business logic.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from django.db import models
from tasks.models import Task, TaskStatus, TaskType
from clients.models import Client
from announcements.models import Announcement, AnnouncementReadStatus

class LoginView(TemplateView):
    """
    Login view for user authentication.
    
    Attributes
    ----------
    template_name : str
        Template name for login page
    
    Methods
    -------
    get(request, *args, **kwargs)
        Handle GET request for login page
    post(request, *args, **kwargs)
        Handle POST request for login form submission
    """
    
    template_name = 'users/login.html'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request for login page."""
        if request.user.is_authenticated:
            return redirect('home')
        form = AuthenticationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        """Handle POST request for login form submission."""
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Добро пожаловать, {user.username}!")
                return redirect('home')
            else:
                messages.error(request, _("Неверное имя пользователя или пароль."))
        else:
            messages.error(request, _("Неверное имя пользователя или пароль."))
        
        return render(request, self.template_name, {'form': form})

class LogoutView(LoginRequiredMixin, TemplateView):
    """
    Logout view for user session termination.
    
    Attributes
    ----------
    login_url : str
        URL to redirect to if user is not authenticated
    
    Methods
    -------
    get(request, *args, **kwargs)
        Handle GET request for logout
    """
    
    login_url = reverse_lazy('login')
    
    def get(self, request, *args, **kwargs):
        """Handle GET request for logout."""
        logout(request)
        messages.success(request, _("Вы успешно вышли из системы."))
        return redirect('login')

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard view showing user-specific information.
    
    Attributes
    ----------
    template_name : str
        Template name for dashboard page
    login_url : str
        URL to redirect to if user is not authenticated
    
    Methods
    -------
    get_context_data(**kwargs)
        Get context data for dashboard template
    """
    
    template_name = 'dashboard.html'
    login_url = reverse_lazy('login')
    
    def get_context_data(self, **kwargs):
        """
        Get context data for dashboard template.

        Returns
        -------
        dict
            Context data containing active tasks, statistics, and announcements
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Import models here to avoid UnboundLocalError
        from tasks.models import Task, TaskStatus, PhotoReport
        from clients.models import Client

        # Get active tasks for employee
        context['active_tasks'] = []
        context['active_tasks_count'] = 0
        context['completion_rate'] = 0  # Initialize to 0

        if user.role == 'EMPLOYEE':
            active_tasks = Task.objects.filter(
                status__in=[TaskStatus.SENT, TaskStatus.REWORK],
                is_active=True
            ).filter(
                models.Q(assigned_to=user) | models.Q(assigned_to__isnull=True)
            )
            context['active_tasks'] = active_tasks
            context['active_tasks_count'] = active_tasks.count()

        # Calculate statistics based on actual completion (like in task list)
        total_planned = 0
        total_completed = 0

        if user.is_superuser or user.role == 'MODERATOR':
            # Для суперпользователя и модератора - все задачи
            all_tasks = Task.objects.all()
        elif user.role == 'EMPLOYEE':
            # Для сотрудника - только его задачи
            all_tasks = Task.objects.filter(
                models.Q(assigned_to=user) |
                models.Q(assigned_to__isnull=True) |
                models.Q(taskemployeeassignment__employee=user)
            ).distinct()

        # --- Статистика для анкет ---
        survey_tasks = all_tasks.filter(task_type='SURVEY', target_count__gt=0)
        for task in survey_tasks:
            total_planned += task.target_count
            total_completed += task.current_count

        # --- Статистика для фотоотчётов ---
        photo_tasks = all_tasks.filter(task_type__in=['EQUIPMENT_PHOTO', 'SIMPLE_PHOTO'])
        for task in photo_tasks:
            assigned_clients = len(task.get_assigned_clients())
            if assigned_clients > 0:
                total_planned += assigned_clients
                submitted_clients = PhotoReport.objects.filter(task=task).values_list('client_id', flat=True).distinct().count()
                total_completed += submitted_clients

        if total_planned > 0:
            context['completion_rate'] = int((total_completed / total_planned) * 100)
        else:
            context['completion_rate'] = 0

        # --- ДОБАВЛЕННЫЙ КОД: Получение объявлений для дашборда ---
        from announcements.models import Announcement, AnnouncementReadStatus
        from django.db.models import Q

        # Get all possible announcements for the current user
        if user.role == 'MODERATOR':
            base_q = Q(target_audience='ALL_USERS') | Q(target_audience='ALL_EMPLOYEES') | Q(target_audience='MODERATORS')
        else:  # EMPLOYEE or CLIENT
            base_q = Q(target_audience='ALL_USERS') | Q(target_audience='ALL_EMPLOYEES')

        announcements = Announcement.objects.filter(
            base_q | Q(target_audience='CUSTOM', recipients=user)
        ).distinct().order_by('-created_at')

        # Add read status information
        for announcement in announcements:
            try:
                read_status = AnnouncementReadStatus.objects.get(announcement=announcement, user=user)
                announcement.is_read = True
                announcement.is_acknowledged = read_status.acknowledged
            except AnnouncementReadStatus.DoesNotExist:
                announcement.is_read = False
                announcement.is_acknowledged = False

        # Sort: unacknowledged first
        announcement_list = list(announcements)
        context['user_announcements'] = sorted(announcement_list, key=lambda x: (x.is_acknowledged, -x.created_at.timestamp()))
        # --- КОНЕЦ ДОБАВЛЕННОГО КОДА ---

        # Add daily tasks to context
        from tasks.models import DailyTask

        # Get daily tasks for the current user (both as creator and assignee)
        # Remove date filter to show all tasks for filtering in JS
        daily_tasks = DailyTask.objects.filter(
            models.Q(creator=user) | models.Q(assignee=user)
        ).order_by('position', '-created_at')

        pass  # Заглушка вместо дебаг-вывода

        context['daily_tasks'] = daily_tasks

        # Get active clients for tasks that might match daily tasks
        active_tasks = Task.objects.filter(
            status__in=[TaskStatus.SENT, TaskStatus.REWORK],
            is_active=True
        ).filter(
            models.Q(assigned_to=user) | models.Q(assigned_to__isnull=True)
        )

        # Build a dictionary with client info: {client_id: {'count': N, 'types': set(), 'latest_task_id': X, 'latest_task_type': Y, 'survey_task_id': A, 'photo_task_id': B}}
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
                    active_clients_data[client_id] = {
                        'count': 0, 
                        'types': set(), 
                        'latest_task_id': None, 
                        'latest_task_date': None, 
                        'latest_task_type': None,
                        'survey_task_id': None,
                        'photo_task_id': None
                    }
                active_clients_data[client_id]['count'] += 1
                active_clients_data[client_id]['types'].add(task_obj.task_type)
                # Track the latest task by created_at
                if active_clients_data[client_id]['latest_task_date'] is None or task_obj.created_at > active_clients_data[client_id]['latest_task_date']:
                    active_clients_data[client_id]['latest_task_id'] = task_obj.id
                    active_clients_data[client_id]['latest_task_date'] = task_obj.created_at
                    active_clients_data[client_id]['latest_task_type'] = task_obj.task_type
                # Track latest survey and photo tasks separately
                if task_obj.task_type == 'SURVEY':
                    if active_clients_data[client_id]['survey_task_id'] is None or task_obj.created_at > active_clients_data[client_id].get('survey_task_date', None):
                        active_clients_data[client_id]['survey_task_id'] = task_obj.id
                        active_clients_data[client_id]['survey_task_date'] = task_obj.created_at
                elif task_obj.task_type in ['EQUIPMENT_PHOTO', 'SIMPLE_PHOTO']:
                    if active_clients_data[client_id]['photo_task_id'] is None or task_obj.created_at > active_clients_data[client_id].get('photo_task_date', None):
                        active_clients_data[client_id]['photo_task_id'] = task_obj.id
                        active_clients_data[client_id]['photo_task_date'] = task_obj.created_at

        # Get active clients queryset
        active_client_ids = set(active_clients_data.keys())
        active_clients = Client.objects.filter(id__in=active_client_ids)
        
        # Add extra data to each client object
        for client in active_clients:
            if client.id in active_clients_data:
                client.tasks_count = active_clients_data[client.id]['count']
                client.tasks_types = active_clients_data[client.id]['types']
                client.latest_task_id = active_clients_data[client.id]['latest_task_id']
                client.latest_task_type = active_clients_data[client.id]['latest_task_type']
                client.survey_task_id = active_clients_data[client.id]['survey_task_id']
                client.photo_task_id = active_clients_data[client.id]['photo_task_id']
            else:
                client.tasks_count = 1
                client.tasks_types = set()
                client.latest_task_id = None
                client.latest_task_type = None
                client.survey_task_id = None
                client.photo_task_id = None

        context['active_clients'] = active_clients

        return context