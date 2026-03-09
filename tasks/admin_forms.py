from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Task, TaskEmployeeAssignment, TaskClientAssignment, DailyTask
from users.models import CustomUser
from clients.models import Client


class DailyTaskForm(forms.ModelForm):
    """Custom form for DailyTask admin with autocomplete client field."""

    # Hidden field to store the selected client ID
    client_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = DailyTask
        fields = '__all__'
        exclude = ('created_at', 'updated_at', 'position', 'client')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Set initial client_id value
        if self.instance and self.instance.pk and self.instance.client_id:
            self.fields['client_id'].initial = self.instance.client_id
        
        # Make creator field readonly and set initial value
        if 'creator' in self.fields:
            self.fields['creator'].widget.attrs['readonly'] = True
            if self.request and not self.instance.pk:
                self.fields['creator'].initial = self.request.user

    def save(self, commit=True):
        """Save the DailyTask with the selected client."""
        instance = super().save(commit=False)

        # Set the client from the client_id field
        client_id = self.cleaned_data.get('client_id')
        if client_id:
            from clients.models import Client
            try:
                instance.client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                instance.client = None
        else:
            instance.client = None
        
        # Set creator from request if not set
        if not instance.pk and self.request and not instance.creator_id:
            instance.creator = self.request.user

        if commit:
            instance.save()

        return instance


class TaskAdminForm(forms.ModelForm):
    """Custom form for Task admin with enhanced assignment functionality."""
    
    # Custom fields for multiple selection
    assigned_employees = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(role='EMPLOYEE'),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='',
            is_stacked=False
        ),
        label=''
    )
    
    assigned_clients = forms.ModelMultipleChoiceField(
        queryset=Client.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='',
            is_stacked=False
        ),
        label=''
    )
    
    class Meta:
        model = Task
        exclude = ('assigned_to', 'client')  # Exclude deprecated fields
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for custom fields
        if self.instance and self.instance.pk:
            # Принудительно обновляем инстанс из базы, чтобы получить актуальные данные
            self.instance.refresh_from_db()
            
            # Initialize employees - get all currently assigned employees
            current_employees = self.instance.taskemployeeassignment_set.select_related('employee')
            employee_ids = [assign.employee.id for assign in current_employees]
            self.fields['assigned_employees'].initial = employee_ids
            
            # Initialize clients - get all currently assigned clients
            current_clients = self.instance.taskclientassignment_set.select_related('client')
            client_ids = [assign.client.id for assign in current_clients]
            self.fields['assigned_clients'].initial = client_ids
        

    
    def save(self, commit=True):
        # Просто вызываем родительский метод, так как сохранение назначений
        # теперь обрабатывается в save_related() админки
        return super().save(commit)