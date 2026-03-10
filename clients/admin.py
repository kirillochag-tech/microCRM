# -*- coding: utf-8 -*-
"""
Admin interface for client management.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Client, ClientGroup


@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):
    """Admin interface for ClientGroup model."""
    list_display = ('name', 'get_client_count', 'created_at')
    search_fields = ('name',)
    list_per_page = 20

    def get_client_count(self, obj):
        """Return number of clients in group."""
        return obj.client_set.count()
    get_client_count.short_description = _('Количество клиентов')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Admin interface for Client model.
    
    NOTE: For 1C import, use management command:
    python manage.py import_clients_from_excel
    """

    list_display = ('name', 'code_1c', 'employee', 'address', 'get_groups', 'get_task_count_display', 'created_at', 'updated_at')
    list_filter = ('client_groups', 'employee')
    search_fields = ('name', 'address', 'code_1c', 'trading_point_name')
    filter_horizontal = ('client_groups',)
    list_per_page = 20

    def get_groups(self, obj):
        """Return comma-separated list of client groups."""
        return ', '.join([group.name for group in obj.client_groups.all()])
    get_groups.short_description = _('Группы')

    def get_task_count_display(self, obj):
        """Return task count display for client."""
        total = obj.get_task_count()
        completed = obj.get_completed_task_count()
        return f"{completed}/{total}"
    get_task_count_display.short_description = _('Задачи (вып./всего)')
