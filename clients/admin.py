# -*- coding: utf-8 -*-
"""
Admin interface for client management with 1C import button.
"""

import os
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.db.models import Count
from openpyxl import load_workbook
from .models import Client, ClientGroup


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Admin interface for Client model with 1C import."""

    list_display = ('name', 'code_1c', 'employee', 'address', 'get_groups', 'created_at', 'updated_at')
    list_filter = ('client_groups', 'employee')
    search_fields = ('name', 'address', 'code_1c', 'trading_point_name')
    filter_horizontal = ('client_groups',)
    list_per_page = 20
    change_list_template = 'admin/clients/client_import_change_list.html'

    def get_urls(self):
        """Add custom import URL."""
        urls = super().get_urls()
        my_urls = [
            path('import-1c/', self.admin_site.admin_view(self.import_1c_view), name='clients_import_1c'),
        ]
        return my_urls + urls

    def import_1c_view(self, request):
        """Custom view for 1C import with clear results."""
        if request.method != 'POST':
            return TemplateResponse(request, 'admin/clients/client_import.html', {
                **self.admin_site.each_context(request),
                'title': 'Импорт клиентов из 1С',
            })

        import_file = request.FILES.get('import_file')
        if not import_file:
            self.message_user(request, 'Ошибка: Файл не выбран', level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:clients_client_changelist'))

        # Process import
        wb = load_workbook(import_file)
        ws = wb.active

        updated = []
        not_found = []
        total = 0

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            code_1c = str(row[1]) if row[1] and str(row[1]).strip() else None
            name = row[2] if len(row) > 2 and row[2] else None

            if not name:
                continue

            total += 1
            instance = None

            # Step 1: Try to find by code_1c
            if code_1c:
                instance = Client.objects.filter(code_1c=code_1c).first()

            # Step 2: If not found, try to find by name
            if not instance and name:
                instance = Client.objects.filter(name=name).first()

            # Step 3: Update if found
            if instance:
                old_code = instance.code_1c
                if code_1c:
                    instance.code_1c = code_1c
                    instance.save()
                
                status = 'updated' if old_code != code_1c else 'unchanged'
                updated.append({
                    'row': row_idx,
                    'id': instance.id,
                    'name': name[:60],
                    'old_code': old_code,
                    'new_code': code_1c,
                    'status': status
                })
            else:
                not_found.append({
                    'row': row_idx,
                    'name': name[:60],
                    'code_1c': code_1c
                })

        # Show results
        return TemplateResponse(request, 'admin/clients/client_import.html', {
            **self.admin_site.each_context(request),
            'title': 'Результаты импорта',
            'total': total,
            'updated': updated,
            'updated_count': len(updated),
            'not_found': not_found,
            'not_found_count': len(not_found),
        })

    def get_groups(self, obj):
        """Return comma-separated list of client groups."""
        return ', '.join([group.name for group in obj.client_groups.all()])
    get_groups.short_description = _('Группы')


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
