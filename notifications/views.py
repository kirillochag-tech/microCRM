from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Notification
from tasks.models import Task
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
@require_http_methods(["GET"])
def get_notifications_count(request):
    """
    Возвращает количество новых уведомлений и задач для текущего пользователя
    """
    user = request.user
    
    # Подсчитываем непрочитанные уведомления
    unread_notifications_count = Notification.objects.filter(
        recipient=user,
        is_read=False
    ).count()
    
    # Подсчитываем задачи, назначенные пользователю
    assigned_tasks_count = Task.objects.filter(
        assigned_to=user
    ).count()
    
    # Подсчитываем задачи, которые требуют действия (например, на проверке)
    tasks_on_check_count = Task.objects.filter(
        assigned_to=user,
        status='ON_CHECK'
    ).count()
    
    # Для модераторов также подсчитываем задачи, созданные ими
    created_tasks_count = 0
    if user.role == 'MODERATOR':
        created_tasks_count = Task.objects.filter(
            created_by=user
        ).count()
    
    return JsonResponse({
        'unread_notifications': unread_notifications_count,
        'assigned_tasks': assigned_tasks_count,
        'tasks_on_check': tasks_on_check_count,
        'created_tasks': created_tasks_count if user.role == 'MODERATOR' else 0,
    })