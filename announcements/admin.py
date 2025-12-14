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
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance exists and if custom_recipients field is present in the form
        if self.instance and self.instance.pk:
            # Only set initial data if the field exists in the form
            if hasattr(self, 'fields') and 'custom_recipients' in self.fields:
                self.fields['custom_recipients'].initial = self.instance.recipients.all()
    
    def save(self, commit=True):
        announcement = super().save(commit=False)
        
        # Handle custom recipients after saving the announcement to get an ID
        if commit:
            announcement.save()
            
            # Clear any existing recipients first
            announcement.recipients.clear()
            
            if announcement.target_audience == 'CUSTOM':
                # Add selected custom recipients
                if 'custom_recipients' in self.cleaned_data:
                    for user in self.cleaned_data['custom_recipients']:
                        # Create the through record
                        AnnouncementRecipient.objects.get_or_create(
                            announcement=announcement,
                            recipient_user=user
                        )
                        # Also add to the M2M field
                        announcement.recipients.add(user)
            elif announcement.target_audience == 'ALL_EMPLOYEES':
                # Add all employees as recipients
                employees = CustomUser.objects.filter(role='EMPLOYEE')
                for employee in employees:
                    # Create the through record
                    AnnouncementRecipient.objects.get_or_create(
                        announcement=announcement,
                        recipient_user=employee
                    )
                    # Also add to the M2M field
                    announcement.recipients.add(employee)
            elif announcement.target_audience == 'MODERATORS':
                # Add all moderators as recipients
                moderators = CustomUser.objects.filter(role='MODERATOR')
                for moderator in moderators:
                    # Create the through record
                    AnnouncementRecipient.objects.get_or_create(
                        announcement=announcement,
                        recipient_user=moderator
                    )
                    # Also add to the M2M field
                    announcement.recipients.add(moderator)
            elif announcement.target_audience == 'ALL_USERS':
                # Add all users as recipients
                all_users = CustomUser.objects.all()
                for user in all_users:
                    # Create the through record
                    AnnouncementRecipient.objects.get_or_create(
                        announcement=announcement,
                        recipient_user=user
                    )
                    # Also add to the M2M field
                    announcement.recipients.add(user)
        
        return announcement


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
    inlines = [AnnouncementRecipientInline]
    
    list_display = ['title', 'author', 'target_audience', 'requires_acknowledgment', 'created_at']
    list_filter = ['target_audience', 'requires_acknowledgment', 'created_at', 'author']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['created_at', 'author']

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = CustomUser.objects.filter(role='MODERATOR')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



