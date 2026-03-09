from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from tasks.models import Task

User = get_user_model()

class Notification(models.Model):
    """
    Модель уведомлений для сотрудников
    """
    NOTIFICATION_TYPES = [
        ('TASK_ASSIGNED', 'Назначена задача'),
        ('TASK_REVIEW', 'Задача на проверке'),
        ('TASK_ACCEPTED', 'Задача принята'),
        ('TASK_REWORK', 'Задача отправлена на доработку'),
        ('NEW_RESPONSE', 'Новый ответ на анкету'),
        ('ANNOUNCEMENT', 'Новое объявление'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Получатель'
    )
    notification_type = models.CharField(
        'Тип уведомления',
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    title = models.CharField('Заголовок', max_length=200)
    message = models.TextField('Сообщение')
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Задача'
    )
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    read_at = models.DateTimeField('Прочитано в', null=True, blank=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.username} - {self.title}'

    def get_absolute_url(self):
        """Возвращает URL для перехода к уведомлению"""
        if self.task:
            return reverse('tasks:task_detail', kwargs={'pk': self.task.pk})
        return reverse('tasks:task_list')