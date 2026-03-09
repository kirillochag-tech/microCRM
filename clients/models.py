"""
Client management models for the employee management system.

This module defines client models and their relationships with users and groups.
"""

import re
from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser, UserRoles

class ClientGroup(models.Model):
    """
    Client group model for organizing clients.
    
    Attributes
    ----------
    name : str
        Name of the client group
    description : str, optional
        Description of the group
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last update timestamp
    """
    
    name = models.CharField(_('Название группы'), max_length=100)
    description = models.TextField(_('Описание'), blank=True, null=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    def __str__(self):
        """Return string representation of client group."""
        return self.name
    
    class Meta:
        verbose_name = _('Группа клиентов')
        verbose_name_plural = _('Группы клиентов')

class Client(models.Model):
    """
    Client model representing external clients.
    
    Attributes
    ----------
    name : str
        Client name (required)
    employee : CustomUser, optional
        Assigned employee (moderator or employee)
    address : str, optional
        Client address
    client_groups : ManyToManyField
        Groups this client belongs to
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last update timestamp
    
    Methods
    -------
    get_assigned_employee()
        Get the employee assigned to this client
    """
    
    name = models.CharField(_('Клиент'), max_length=200, db_index=True)
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role__in': [UserRoles.EMPLOYEE, UserRoles.MODERATOR]},
        verbose_name=_('Сотрудник')
    )
    address = models.CharField(_('Адрес'), max_length=300, blank=True, null=True)
    trading_point_name = models.CharField(_('Название торговой точки'), max_length=200, blank=True, null=True)
    trading_point_address = models.CharField(_('Адрес торговой точки'), max_length=300, blank=True, null=True)
    stand_count = models.PositiveIntegerField(
        _('Количество стендов'),
        default=0,
        help_text=_('Официальное количество стендов у клиента')
    )
    code_1c = models.CharField(
        _('Код 1С'),
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text=_('Уникальный код клиента из системы 1С. Используется для синхронизации при изменении наименования контрагента.')
    )
    client_groups = models.ManyToManyField(
        ClientGroup,
        blank=True,
        verbose_name=_('Группы')
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    def __str__(self):
        """Return string representation of client."""
        return self.name
    
    def clean(self):
        """Очистка поля name от неразрывных пробелов и лишних символов."""
        if self.name:
            # Заменяем неразрывные пробелы, табы, переносы на обычные пробелы
            self.name = re.sub(r'[\xa0\t\n\r]+', ' ', self.name)
            # Убираем лишние пробелы
            self.name = re.sub(r'\s+', ' ', self.name).strip()
        super().clean()
    
    def save(self, *args, **kwargs):
        self.full_clean()  # вызываем clean перед сохранением
        super().save(*args, **kwargs)
    
    def get_assigned_employee(self):
        """Get the employee assigned to this client."""
        return self.employee

    def get_task_count(self):
        """Get count of tasks associated with this client."""
        return self.tasks.count()

    def get_completed_task_count(self):
        """Get count of completed tasks for this client."""
        from tasks.models import TaskStatus
        return self.tasks.filter(status=TaskStatus.COMPLETED).count()
    
    class Meta:
        verbose_name = _('Клиент')
        verbose_name_plural = _('Клиенты')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),  # Index for faster search
            models.Index(fields=['code_1c']),  # Index for 1C code lookup
        ]