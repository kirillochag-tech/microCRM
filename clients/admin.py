# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 20:58:43 2025

@author: Professional
"""

"""
Admin interface for client management.

This module defines the admin interface configuration for client models.
Provides Russian language interface and inline editing capabilities.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Client, ClientGroup


class ClientResource(resources.ModelResource):
    """Resource class for importing/exporting Client model."""
    
    class Meta:
        model = Client
        import_id_fields = ['name']
        fields = ('name', 'employee__username', 'client_groups__name', 'trading_point_name', 'trading_point_address')
        # Define the human-readable field names for import
        export_order = ('name', 'employee__username', 'client_groups__name', 'trading_point_name', 'trading_point_address')

class ClientInline(admin.TabularInline):
    """Inline client editing for client groups."""
    model = Client.client_groups.through
    extra = 1
    verbose_name = _('Клиент')
    verbose_name_plural = _('Клиенты')

@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):
    """
    Admin interface for ClientGroup model.
    
    Provides inline editing of clients within groups.
    """
    
    inlines = [ClientInline]
    list_display = ('name', 'get_client_count', 'created_at')
    search_fields = ('name',)
    list_per_page = 20
    
    def get_client_count(self, obj):
        """Return number of clients in group."""
        return obj.client_set.count()
    get_client_count.short_description = _('Количество клиентов')
    
    class Meta:
        verbose_name = _('Группа клиентов')
        verbose_name_plural = _('Группы клиентов')

@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin):
    """
    Admin interface for Client model.
    
    Provides comprehensive client management interface with import/export functionality.
    """
    
    resource_class = ClientResource
    list_display = ('name', 'employee', 'address', 'get_groups', 'created_at')
    list_filter = ('client_groups', 'employee')
    search_fields = ('name', 'address')
    filter_horizontal = ('client_groups',)
    list_per_page = 20
    
    def get_groups(self, obj):
        """Return comma-separated list of client groups."""
        return ', '.join([group.name for group in obj.client_groups.all()])
    get_groups.short_description = _('Группы')
    
    class Meta:
        verbose_name = _('Клиент')
        verbose_name_plural = _('Клиенты')