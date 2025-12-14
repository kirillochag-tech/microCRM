# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 20:58:07 2025

@author: Professional
"""

"""
Admin interface for user management.

This module defines the admin interface configuration for user models.
Provides Russian language interface and custom display options.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserRoles

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin interface for CustomUser model.
    
    Extends Django's built-in UserAdmin to include custom fields
    and provide Russian language interface.
    """
    
    # Добавляем кастомные поля в существующие поля админки
    fieldsets = UserAdmin.fieldsets + (
        (_('Дополнительная информация'), {
            'fields': ('role', 'phone'),
        }),
    )
    
    # Поля для отображения в списке пользователей
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'is_superuser', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Фильтрация по ролям
    def get_queryset(self, request):
        """Optimize queryset by selecting related fields."""
        return super().get_queryset(request).select_related()
    
    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')