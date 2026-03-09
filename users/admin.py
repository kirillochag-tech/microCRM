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

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserRoles, EmployeeGroup

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
        (_('Группы'), {
            'fields': ('employee_groups',),
            'classes': ('collapse',)
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


class EmployeeGroupForm(forms.ModelForm):
    """
    Custom form for EmployeeGroup admin interface.
    
    Adds a convenient widget for selecting employees to add to the group.
    """
    
    employees = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(role=UserRoles.EMPLOYEE),
        widget=admin.widgets.FilteredSelectMultiple(_('Сотрудники'), False),
        required=False,
        label=_('Сотрудники')
    )
    
    class Meta:
        model = EmployeeGroup
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Use direct ManyToMany field for initialization
            self.fields['employees'].initial = CustomUser.objects.filter(employee_groups=self.instance)


@admin.register(EmployeeGroup)
class EmployeeGroupAdmin(admin.ModelAdmin):
    form = EmployeeGroupForm
    list_display = ('name', 'get_employee_count', 'created_at')
    search_fields = ('name',)
    list_per_page = 20

    def get_employee_count(self, obj):
        return CustomUser.objects.filter(employee_groups=obj).count()
    get_employee_count.short_description = _('Количество сотрудников')
    
    def save_model(self, request, obj, form, change):
        """Handle saving of the model and its ManyToMany relationships."""
        
        # Save the group first
        super().save_model(request, obj, form, change)
        
        # Handle employees ManyToMany relationship
        if 'employees' in form.cleaned_data:
            new_employees = form.cleaned_data['employees']
            new_employee_pks = {e.pk for e in new_employees}
            
            # Get current employees in this group
            current_employee_pks = set(CustomUser.objects.filter(employee_groups=obj).values_list('pk', flat=True))
            
            # Remove group from employees who are not in the new list
            to_remove = current_employee_pks - new_employee_pks
            if to_remove:
                for employee in CustomUser.objects.filter(pk__in=to_remove):
                    employee.employee_groups.remove(obj)
            
            # Add group to new employees
            to_add = new_employee_pks - current_employee_pks
            if to_add:
                for employee in CustomUser.objects.filter(pk__in=to_add):
                    employee.employee_groups.add(obj)