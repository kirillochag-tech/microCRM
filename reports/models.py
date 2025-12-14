"""
Reporting and analytics models.

This module defines models for storing aggregated statistics and analytics data.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser, UserRoles  # Исправленный импорт
from clients.models import Client, ClientGroup
from tasks.models import Task, TaskType

class TaskStatistics(models.Model):
    """
    Aggregated task statistics model.
    
    Stores pre-calculated statistics for performance optimization.
    """
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='report_statistics_tasks')
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Клиент')
    )
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': UserRoles.EMPLOYEE},  # Исправлено
        null=True,
        blank=True,
        verbose_name=_('Сотрудник')
    )
    moderator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': UserRoles.MODERATOR},  # Исправлено
        related_name='moderator_stats',
        null=True,
        blank=True,
        verbose_name=_('Модератор')
    )
    client_group = models.ForeignKey(
        ClientGroup,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Группа клиентов')
    )
    
    # Статистика для анкет
    total_responses = models.PositiveIntegerField(_('Всего ответов'), default=0)
    completed_tasks = models.PositiveIntegerField(_('Завершено задач'), default=0)
    pending_tasks = models.PositiveIntegerField(_('В процессе'), default=0)
    
    # JSON поле для хранения детальной статистики по вопросам
    survey_stats = models.JSONField(_('Статистика анкет'), null=True, blank=True)
    
    last_updated = models.DateTimeField(_('Последнее обновление'), auto_now=True)
    
    def __str__(self):
        return f"Статистика для {self.task.title}"
    
    class Meta:
        verbose_name = _('Статистика задачи')
        verbose_name_plural = _('Статистика задач')
        unique_together = ('task', 'client', 'employee')
