from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from tasks.models import Task, SurveyAnswer, PhotoReport
from announcements.models import Announcement
from .models import Notification

User = get_user_model()

@receiver(post_save, sender=Task)
def task_assigned_notification(sender, instance, created, **kwargs):
    """
    Отправляет уведомление сотруднику, когда ему назначается задача
    """
    if created and instance.assigned_to:
        # Создаем уведомление для сотрудника, которому назначена задача
        Notification.objects.create(
            recipient=instance.assigned_to,
            notification_type='TASK_ASSIGNED',
            title=f'Назначена задача: {instance.title}',
            message=f'Вам назначена новая задача: {instance.title}',
            task=instance
        )
    
    # Отправляем уведомление модератору, если задача создана или изменена
    if instance.created_by:
        # Уведомляем модератора, который создал задачу
        Notification.objects.create(
            recipient=instance.created_by,
            notification_type='TASK_ASSIGNED',
            title=f'Создана задача: {instance.title}',
            message=f'Вами создана задача: {instance.title}',
            task=instance
        )

@receiver(post_save, sender=SurveyAnswer)
def survey_answer_notification(sender, instance, created, **kwargs):
    """
    Отправляет уведомление модератору, когда получен новый ответ на анкету
    """
    if created:
        # Находим модераторов, которые могут обрабатывать ответы
        moderators = User.objects.filter(role='MODERATOR')
        
        for moderator in moderators:
            Notification.objects.create(
                recipient=moderator,
                notification_type='NEW_RESPONSE',
                title=f'Новый ответ на анкету',
                message=f'Получен новый ответ от {instance.user.username} на вопрос "{instance.question.question_text[:50]}..."',
                task=instance.question.task
            )
        
        # Также уведомляем модератора, который создал задачу
        if instance.question.task.created_by:
            Notification.objects.create(
                recipient=instance.question.task.created_by,
                notification_type='NEW_RESPONSE',
                title=f'Новый ответ на анкету',
                message=f'Получен новый ответ от {instance.user.username} на анкету "{instance.question.task.title}"',
                task=instance.question.task
            )

@receiver(post_save, sender=PhotoReport)
def photo_report_notification(sender, instance, created, **kwargs):
    """
    Отправляет уведомление модератору, когда получен новый фотоотчет
    """
    if created:
        # Находим модераторов, которые могут обрабатывать фотоотчеты
        moderators = User.objects.filter(role='MODERATOR')
        
        for moderator in moderators:
            Notification.objects.create(
                recipient=moderator,
                notification_type='NEW_RESPONSE',
                title=f'Новый фотоотчет',
                message=f'Получен новый фотоотчет от {instance.created_by.username} для клиента {instance.client.name}',
                task=instance.task
            )
        
        # Также уведомляем модератора, который создал задачу
        if instance.task.created_by:
            Notification.objects.create(
                recipient=instance.task.created_by,
                notification_type='NEW_RESPONSE',
                title=f'Новый фотоотчет',
                message=f'Получен новый фотоотчет от {instance.created_by.username} для задачи "{instance.task.title}"',
                task=instance.task
            )

@receiver(post_save, sender=Announcement)
def announcement_notification(sender, instance, created, **kwargs):
    """
    Отправляет уведомление всем сотрудникам, когда создано новое объявление
    """
    if created:
        # Находим всех сотрудников
        employees = User.objects.filter(role='EMPLOYEE')
        
        for employee in employees:
            Notification.objects.create(
                recipient=employee,
                notification_type='ANNOUNCEMENT',
                title=f'Новое объявление: {instance.title}',
                message=f'{instance.title}',
                task=None  # Объявления не связаны с задачами
            )
        
        # Также уведомляем всех модераторов
        moderators = User.objects.filter(role='MODERATOR')
        
        for moderator in moderators:
            Notification.objects.create(
                recipient=moderator,
                notification_type='ANNOUNCEMENT',
                title=f'Новое объявление: {instance.title}',
                message=f'{instance.title}',
                task=None  # Объявления не связаны с задачами
            )

@receiver(post_save, sender=Task)
def task_status_change_notification(sender, instance, **kwargs):
    """
    Отправляет уведомления при изменении статуса задачи
    """
    # Проверяем, изменился ли статус
    if instance.status == 'ON_CHECK':
        # Отправляем уведомление сотруднику, что задача на проверке
        if instance.assigned_to:
            Notification.objects.create(
                recipient=instance.assigned_to,
                notification_type='TASK_REVIEW',
                title=f'Задача на проверке: {instance.title}',
                message=f'Ваша задача "{instance.title}" находится на проверке у модератора',
                task=instance
            )
        
        # Отправляем уведомление модератору, что задача на проверке
        if instance.created_by:
            Notification.objects.create(
                recipient=instance.created_by,
                notification_type='TASK_REVIEW',
                title=f'Задача на проверке: {instance.title}',
                message=f'Задача "{instance.title}" находится на проверке у модератора',
                task=instance
            )
    elif instance.status == 'ACCEPTED':
        # Отправляем уведомление сотруднику, что задача принята
        if instance.assigned_to:
            Notification.objects.create(
                recipient=instance.assigned_to,
                notification_type='TASK_ACCEPTED',
                title=f'Задача принята: {instance.title}',
                message=f'Ваша задача "{instance.title}" была принята модератором',
                task=instance
            )
        
        # Отправляем уведомление модератору, что задача принята
        if instance.created_by:
            Notification.objects.create(
                recipient=instance.created_by,
                notification_type='TASK_ACCEPTED',
                title=f'Задача принята: {instance.title}',
                message=f'Задача "{instance.title}", которую вы создали, была принята',
                task=instance
            )
    elif instance.status == 'REWORK':
        # Отправляем уведомление сотруднику, что задача отправлена на доработку
        if instance.assigned_to:
            Notification.objects.create(
                recipient=instance.assigned_to,
                notification_type='TASK_REWORK',
                title=f'Задача на доработке: {instance.title}',
                message=f'Ваша задача "{instance.title}" отправлена на доработку. Комментарий модератора: {instance.moderator_comment or "Без комментария"}',
                task=instance
            )
        
        # Отправляем уведомление модератору, что задача отправлена на доработку
        if instance.created_by:
            Notification.objects.create(
                recipient=instance.created_by,
                notification_type='TASK_REWORK',
                title=f'Задача на доработке: {instance.title}',
                message=f'Задача "{instance.title}", которую вы создали, отправлена на доработку. Комментарий модератора: {instance.moderator_comment or "Без комментария"}',
                task=instance
            )