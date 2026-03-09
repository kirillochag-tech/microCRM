from django.contrib import admin
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Announcement, AnnouncementRecipient, AnnouncementReadStatus
from users.models import CustomUser
from django.db.models import Q
from django.contrib.auth.models import User, Group
from django.db import models



class AnnouncementRecipientInline(admin.TabularInline):
    model = AnnouncementRecipient
    extra = 1
    verbose_name = _('Получатель')
    verbose_name_plural = _('Получатели')


class AnnouncementAdminForm(forms.ModelForm):
    """Custom form for Announcement admin with recipient selection."""
    
    custom_recipients = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        required=False,
        widget=admin.widgets.FilteredSelectMultiple(
            verbose_name=_('Пользователи'),
            is_stacked=False
        ),
        label=_('Выбранные пользователи')
    )
    
    class Meta:
        model = Announcement
        exclude = ('recipients',)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance exists and if custom_recipients field is present in the form
        if self.instance and self.instance.pk:
            # Only set initial data if the field exists in the form
            if hasattr(self, 'fields') and 'custom_recipients' in self.fields:
                self.fields['custom_recipients'].initial = self.instance.recipients.all()


# @admin.register(Announcement)
class AnnouncementReadStatusInline(admin.TabularInline):
    model = AnnouncementReadStatus
    extra = 0
    readonly_fields = ('user', 'read_at')

@admin.register(AnnouncementReadStatus)
class AnnouncementReadStatusAdmin(admin.ModelAdmin):
    list_display = ['announcement', 'user', 'read_at', 'acknowledged']
    list_filter = ['acknowledged', 'read_at', 'announcement__title']
    search_fields = ['user__username', 'announcement__title']
    readonly_fields = ['read_at']

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementAdminForm
    inlines = []  # AnnouncementRecipientInline отключен
    
    list_display = ['title', 'author', 'target_audience', 'requires_acknowledgment', 'acknowledged_ratio', 'created_at']
    list_filter = ['target_audience', 'requires_acknowledgment', 'created_at', 'author']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['created_at', 'author', 'acknowledged_ratio']

    def get_fieldsets(self, request, obj=None):
        basic_fields = ['title', 'content', 'requires_acknowledgment', 'target_audience']
        
        fieldsets = [
            (_('Основная информация'), {
                'fields': basic_fields
            }),
        ]
        
        # Show recipients field only if target audience is CUSTOM
        if obj and obj.target_audience == 'CUSTOM':
            fieldsets.append(
                (_('Получатели'), {
                    'fields': ['custom_recipients'],
                })
            )
        
        fieldsets.append(
            (_('Дополнительная информация'), {
                'fields': ['created_at', 'author'],
                'classes': ['collapse']
            })
        )
        
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Only include custom_recipients field if target_audience is CUSTOM
        if not obj or obj.target_audience != 'CUSTOM':
            if 'custom_recipients' in form.base_fields:
                del form.base_fields['custom_recipients']
        return form

    def save_model(self, request, obj, form, change):
        if not change:  # При создании новой записи
            obj.author = request.user
        super().save_model(request, obj, form, change)
        
        # После сохранения объекта, обновляем получателей
        # Сначала удаляем всех существующих получателей для этого объявления
        AnnouncementRecipient.objects.filter(announcement=obj).delete()
        
        # Определяем целевой набор получателей в зависимости от аудитории
        target_users = CustomUser.objects.none()
        if obj.target_audience == 'CUSTOM':
            target_users = form.cleaned_data.get('custom_recipients', CustomUser.objects.none())
        elif obj.target_audience == 'ALL_EMPLOYEES':
            target_users = CustomUser.objects.filter(role='EMPLOYEE')
        elif obj.target_audience == 'MODERATORS':
            target_users = CustomUser.objects.filter(role='MODERATOR')
        elif obj.target_audience == 'ALL_USERS':
            target_users = CustomUser.objects.all()

        # Создаем новые связи
        for user in target_users:
            AnnouncementRecipient.objects.create(
                announcement=obj,
                recipient_user=user
            )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = CustomUser.objects.filter(role='MODERATOR')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



