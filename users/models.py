"""
User management models for the employee management system.

This module defines custom user models and role-based permissions.
Implements SOLID principles by separating user authentication from business logic.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator

class Role(models.TextChoices):
    """User roles enumeration."""
    EMPLOYEE = 'EMPLOYEE', _('Сотрудник')
    MODERATOR = 'MODERATOR', _('Модератор')
    CLIENT = 'CLIENT', _('Клиент')

class CustomUser(AbstractUser):
    """
    Custom user model extending AbstractUser.
    
    Attributes
    ----------
    role : str
        User role (EMPLOYEE, MODERATOR, CLIENT)
    phone : str, optional
        User phone number
    groups : ManyToManyField
        User groups for permissions
    user_permissions : ManyToManyField
        Specific user permissions
    
    Methods
    -------
    is_employee()
        Check if user is an employee
    is_moderator()
        Check if user is a moderator
    is_client()
        Check if user is a client
    """
    
    role = models.CharField(
        _('Роль'),
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE
    )
    phone = models.CharField(
        _('Телефон'),
        max_length=20,
        blank=True,
        null=True
    )
    
    # Override groups and permissions to avoid clashes
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='customuser_set',
        related_query_name='customuser',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='customuser_set',
        related_query_name='customuser',
    )
    
    def __str__(self):
        """Return string representation of user."""
        return f"{self.username} ({self.get_role_display()})"
    
    def is_employee(self):
        """Check if user has employee role."""
        return self.role == Role.EMPLOYEE
    
    def is_moderator(self):
        """Check if user has moderator role."""
        return self.role == Role.MODERATOR
    
    def is_client(self):
        """Check if user has client role."""
        return self.role == Role.CLIENT
    
    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')

# Экспортируем Role для использования в других модулях
UserRoles = Role