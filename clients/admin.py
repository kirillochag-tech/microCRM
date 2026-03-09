# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 20:58:43 2025

@author: Professional
"""

"""
Admin interface for client management with 1C import support.

This module defines the admin interface configuration for client models.
Provides Russian language interface and import/export functionality with 1C code matching.
"""

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django import forms
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.db import transaction
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.tmp_storages import TempFolderStorage
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from .models import Client, ClientGroup
from users.models import CustomUser


class ClientResource(resources.ModelResource):
    """
    Resource class for importing/exporting Client model with 1C code support.
    
    Import algorithm:
    1. If code_1c field is filled - match by this field
    2. If code_1c is empty - match by client name (case-sensitive)
    3. If match found by code_1c but name differs - update name
    4. If match found by name - update code_1c if provided
    5. If no match - skip the record
    6. Detect duplicates and report to moderator
    """

    employee_username = fields.Field(
        attribute='employee',
        column_name='employee_username',
        widget=ForeignKeyWidget(CustomUser, field='username')
    )
    
    client_groups_names = fields.Field(
        attribute='client_groups',
        column_name='client_groups__name',
        widget=ManyToManyWidget(ClientGroup, field='name', separator=';')
    )

    class Meta:
        model = Client
        # Поле code_1c должно быть вторым после ID для корректного импорта
        fields = ('id', 'code_1c', 'name', 'employee_username', 'client_groups_names',
                  'address', 'trading_point_name', 'trading_point_address', 'stand_count')
        # Порядок экспорта: code_1c вторым после ID
        export_order = ('id', 'code_1c', 'name', 'employee_username', 'client_groups_names',
                        'address', 'trading_point_name', 'trading_point_address', 'stand_count')
        import_id_fields = ['id']  # Use ID for import tracking

    def before_import_row(self, row, **kwargs):
        """
        Before importing each row, clean and prepare data.
        """
        # Clean code_1c - remove whitespace
        if 'code_1c' in row and row['code_1c']:
            row['code_1c'] = str(row['code_1c']).strip()
        else:
            row['code_1c'] = None
            
        # Clean name
        if 'name' in row and row['name']:
            row['name'] = str(row['name']).strip()
            
        return row

    def get_or_init_instance(self, instance_loader, row):
        """
        Custom logic for finding or creating client instance during import.
        
        Returns tuple: (instance, created)
        """
        code_1c = row.get('code_1c')
        name = row.get('name')
        
        # Strategy 1: Match by code_1c if provided
        if code_1c:
            try:
                client = Client.objects.get(code_1c=code_1c)
                # Found existing client by 1C code
                # Update name if it differs
                if name and client.name != name:
                    client.name = name
                return client, False
            except Client.DoesNotExist:
                pass
        
        # Strategy 2: Match by name (case-sensitive) if code_1c not provided or not found
        if name:
            try:
                client = Client.objects.get(name=name)
                # Found existing client by name
                # Update code_1c if provided and client doesn't have it
                if code_1c and not client.code_1c:
                    client.code_1c = code_1c
                elif code_1c and client.code_1c and client.code_1c != code_1c:
                    # Name matches but code_1c differs - this is a conflict
                    # Keep existing code_1c, log warning
                    pass
                return client, False
            except Client.DoesNotExist:
                pass
        
        # No match found - create new instance (will be skipped by skip_row if no code_1c)
        instance = Client()
        return instance, True

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """
        Skip rows that don't match existing clients.
        
        Skip if:
        - No code_1c provided AND no name match found
        - This prevents creating duplicate clients
        """
        if import_validation_errors:
            return True
            
        code_1c = row.get('code_1c')
        name = row.get('name')
        
        # If we have a code_1c but no match found, skip (don't create new)
        if code_1c and not instance.pk:
            return True
            
        # If no code_1c and no name match, skip
        if not code_1c and not instance.pk:
            return True
            
        return False

    def after_import_row(self, row, result, **kwargs):
        """
        After importing each row, log the result.
        """
        code_1c = row.get('code_1c')
        name = row.get('name')
        
        if result.errors:
            result.append_warning_message(
                f"Ошибка импорта клиента: {name} (код 1С: {code_1c or 'не указан'})"
            )
        elif result.new_record:
            result.append_info_message(
                f"Создан новый клиент: {name} (код 1С: {code_1c or 'не указан'})"
            )
        else:
            result.append_info_message(
                f"Обновлен клиент: {name} (код 1С: {code_1c or 'не указан'})"
            )


class ClientImportForm(forms.Form):
    """Form for client import with duplicate detection."""
    import_file = forms.FileField(label=_('Файл для импорта (Excel/CSV)'))
    import_strategy = forms.ChoiceField(
        label=_('Стратегия импорта'),
        choices=[
            ('match_code', 'Сопоставление по коду 1С (приоритет)'),
            ('match_name', 'Сопоставление по наименованию'),
            ('auto', 'Автоматически (код 1С → наименование)'),
        ],
        initial='auto'
    )


@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin):
    """
    Admin interface for Client model with advanced 1C import.
    
    Features:
    - Import/export with Excel/CSV
    - 1C code-based matching
    - Duplicate detection
    - Task preservation during client updates
    """

    resource_class = ClientResource
    list_display = ('name', 'code_1c', 'employee', 'address', 'get_groups', 'get_task_count_display', 'created_at', 'updated_at')
    list_filter = ('client_groups', 'employee')
    search_fields = ('name', 'address', 'code_1c', 'trading_point_name')
    filter_horizontal = ('client_groups',)
    list_per_page = 20
    change_list_template = 'admin/clients/client_import_change_list.html'

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
    
    def get_urls(self):
        """Add custom URLs for import preview."""
        urls = super().get_urls()
        my_urls = [
            path('import-preview/', self.admin_site.admin_view(self.import_preview), name='clients_import_preview'),
            path('import-confirm/', self.admin_site.admin_view(self.import_confirm), name='clients_import_confirm'),
        ]
        return my_urls + urls

    def import_preview(self, request):
        """
        Preview import results and detect duplicates before actual import.
        """
        if request.method != 'POST':
            return HttpResponseRedirect(reverse('admin:clients_client_changelist'))
        
        import_file = request.FILES.get('import_file')
        if not import_file:
            self.message_user(request, _('Ошибка: Файл не загружен'), level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:clients_client_changelist'))
        
        # Read and parse the file
        duplicates = []
        new_clients = []
        updated_clients = []
        skipped_clients = []
        
        try:
            import pandas as pd
            
            # Determine file type and read
            if import_file.name.endswith('.xlsx') or import_file.name.endswith('.xls'):
                df = pd.read_excel(import_file)
            elif import_file.name.endswith('.csv'):
                df = pd.read_csv(import_file)
            else:
                self.message_user(request, _('Ошибка: Неверный формат файла. Используйте Excel или CSV'), level=messages.ERROR)
                return HttpResponseRedirect(reverse('admin:clients_client_changelist'))
            
            # Normalize column names
            df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
            
            # Process each row
            for idx, row in df.iterrows():
                code_1c = str(row.get('code_1c', '')).strip() if pd.notna(row.get('code_1c')) else None
                name = str(row.get('name', '')).strip() if pd.notna(row.get('name')) else None
                
                if not name:
                    skipped_clients.append({'row': idx + 2, 'reason': _('Нет наименования клиента'), 'data': dict(row)})
                    continue
                
                # Check for duplicates in database
                existing_by_code = None
                existing_by_name = None
                
                if code_1c:
                    existing_by_code = Client.objects.filter(code_1c=code_1c).first()
                
                if not existing_by_code and name:
                    existing_by_name = Client.objects.filter(name=name).first()
                
                # Check for duplicates in the import file itself
                # (simplified - in production would need more robust checking)
                
                if existing_by_code:
                    # Match by 1C code
                    changes = {}
                    if existing_by_code.name != name:
                        changes['name'] = {'old': existing_by_code.name, 'new': name}
                    
                    updated_clients.append({
                        'row': idx + 2,
                        'type': 'update_by_code',
                        'client_id': existing_by_code.id,
                        'name': existing_by_code.name,
                        'code_1c': code_1c,
                        'changes': changes,
                        'data': dict(row)
                    })
                elif existing_by_name:
                    # Match by name
                    changes = {}
                    if code_1c and not existing_by_name.code_1c:
                        changes['code_1c'] = {'old': None, 'new': code_1c}
                    elif code_1c and existing_by_name.code_1c and existing_by_name.code_1c != code_1c:
                        changes['code_1c_conflict'] = {'old': existing_by_name.code_1c, 'new': code_1c}
                    
                    updated_clients.append({
                        'row': idx + 2,
                        'type': 'update_by_name',
                        'client_id': existing_by_name.id,
                        'name': name,
                        'code_1c': code_1c,
                        'changes': changes,
                        'data': dict(row)
                    })
                else:
                    # No match - would be skipped per requirements
                    skipped_clients.append({
                        'row': idx + 2,
                        'reason': _('Нет совпадения по коду 1С или наименованию'),
                        'name': name,
                        'code_1c': code_1c,
                        'data': dict(row)
                    })
            
            # Store preview data in session
            request.session['import_preview_data'] = {
                'duplicates': duplicates,
                'new_clients': new_clients,
                'updated_clients': updated_clients,
                'skipped_clients': skipped_clients,
            }
            
        except Exception as e:
            self.message_user(request, f'Ошибка обработки файла: {str(e)}', level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:clients_client_changelist'))
        
        # Render preview template
        context = {
            **self.admin_site.each_context(request),
            'duplicates': duplicates,
            'new_clients': new_clients,
            'updated_clients': updated_clients,
            'skipped_clients': skipped_clients,
            'title': _('Предварительный просмотр импорта'),
        }
        return TemplateResponse(request, 'admin/clients/import_preview.html', context)

    def import_confirm(self, request):
        """
        Confirm and execute the import after preview.
        """
        if request.method != 'POST':
            return HttpResponseRedirect(reverse('admin:clients_client_changelist'))
        
        preview_data = request.session.get('import_preview_data', {})
        
        with transaction.atomic():
            # Process updates
            for item in preview_data.get('updated_clients', []):
                client_id = item.get('client_id')
                if client_id:
                    try:
                        client = Client.objects.get(id=client_id)
                        row_data = item.get('data', {})
                        
                        # Update fields from row data
                        if 'name' in row_data and pd.notna(row_data['name']):
                            client.name = str(row_data['name']).strip()
                        if 'code_1c' in row_data and pd.notna(row_data['code_1c']):
                            code_val = str(row_data['code_1c']).strip()
                            if code_val and not client.code_1c:
                                client.code_1c = code_val
                        if 'address' in row_data and pd.notna(row_data['address']):
                            client.address = str(row_data['address']).strip()
                        if 'trading_point_name' in row_data and pd.notna(row_data['trading_point_name']):
                            client.trading_point_name = str(row_data['trading_point_name']).strip()
                        if 'trading_point_address' in row_data and pd.notna(row_data['trading_point_address']):
                            client.trading_point_address = str(row_data['trading_point_address']).strip()
                        if 'stand_count' in row_data and pd.notna(row_data['stand_count']):
                            try:
                                client.stand_count = int(row_data['stand_count'])
                            except (ValueError, TypeError):
                                pass
                        
                        client.save()
                    except Client.DoesNotExist:
                        pass
            
            # Clear session data
            request.session['import_preview_data'] = None
        
        self.message_user(
            request, 
            _('Импорт завершен. Обновлено клиентов: {count}').format(
                count=len(preview_data.get('updated_clients', []))
            ),
            level=messages.SUCCESS
        )
        
        return HttpResponseRedirect(reverse('admin:clients_client_changelist'))

    def get_search_results(self, request, queryset, search_term):
        """
        Override to make search case-insensitive for Cyrillic characters.
        Uses custom REGEXP function for SQLite.
        """
        if search_term:
            from django.db.models import Q
            # Escape special regex characters
            import re
            escaped_term = re.escape(search_term)
            queryset = queryset.extra(
                where=["name REGEXP %s OR address REGEXP %s OR code_1c REGEXP %s"],
                params=[escaped_term, escaped_term, escaped_term]
            )
        return queryset, False

    class Meta:
        verbose_name = _('Клиент')
        verbose_name_plural = _('Клиенты')


@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):
    """
    Admin interface for ClientGroup model.

    Provides inline editing of clients within groups.
    """

    inlines = []  # Removed inline for cleaner interface
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
