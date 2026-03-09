# tasks/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _ 
from .models import SurveyAnswer, SurveyAnswerPhoto, SurveyQuestion, Client, SurveyQuestionChoice, Task, TaskStatus
from users.models import CustomUser
import logging

logger = logging.getLogger(__name__)

class SurveyResponseForm(forms.Form):
    """
    Форма для заполнения анкеты с одиночной загрузкой фото.
    Для множественной загрузки используется JavaScript.
    """
    
    def __init__(self, task, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = task
        self.user = user
        
        if not task.client:
            # We'll handle client selection in the save method using POST data
            pass
        
        for question in task.questions.all().order_by('order'):
            field_name = f'question_{question.id}'
            
            if question.question_type == 'RADIO':
                if question.choices.exists():
                    choices = [(choice.id, choice.choice_text) for choice in question.choices.all()]
                    self.fields[field_name] = forms.ChoiceField(
                        label=question.question_text,
                        choices=choices,
                        widget=forms.RadioSelect(),
                        required=True
                    )
                else:
                    self.fields[field_name] = forms.ChoiceField(
                        label=question.question_text,
                        choices=[('да', 'Да'), ('нет', 'Нет')],
                        widget=forms.RadioSelect(),
                        required=True
                    )
                    
            elif question.question_type == 'CHECKBOX':
                if question.choices.exists():
                    choices = [(choice.id, choice.choice_text) for choice in question.choices.all()]
                    self.fields[field_name] = forms.MultipleChoiceField(
                        label=question.question_text,
                        choices=choices,
                        widget=forms.CheckboxSelectMultiple(),
                        required=False
                    )
                else:
                    self.fields[field_name] = forms.MultipleChoiceField(
                        label=question.question_text,
                        choices=[('да', 'Да'), ('нет', 'Нет')],
                        widget=forms.CheckboxSelectMultiple(),
                        required=False
                    )
                    
            elif question.question_type == 'TEXT':
                self.fields[field_name] = forms.CharField(
                    label=question.question_text,
                    widget=forms.Textarea(attrs={'rows': 3}),
                    required=False
                )
                
            elif question.question_type == 'TEXT_SHORT':
                self.fields[field_name] = forms.CharField(
                    label=question.question_text,
                    widget=forms.TextInput(),
                    required=False,
                    max_length=60
                )
                
            elif question.question_type == 'SELECT_SINGLE':
                if question.choices.exists():
                    choices = [('', '---')] + [(choice.id, choice.choice_text) for choice in question.choices.all()]
                    self.fields[field_name] = forms.ChoiceField(
                        label=question.question_text,
                        choices=choices,
                        widget=forms.Select(),
                        required=False
                    )
                else:
                    self.fields[field_name] = forms.ChoiceField(
                        label=question.question_text,
                        choices=[('', '---'), ('да', 'Да'), ('нет', 'Нет')],
                        widget=forms.Select(),
                        required=False
                    )
                    
            elif question.question_type == 'SELECT_MULTIPLE':
                if question.choices.exists():
                    choices = [(choice.id, choice.choice_text) for choice in question.choices.all()]
                    self.fields[field_name] = forms.MultipleChoiceField(
                        label=question.question_text,
                        choices=choices,
                        widget=forms.SelectMultiple(),
                        required=False
                    )
                else:
                    self.fields[field_name] = forms.MultipleChoiceField(
                        label=question.question_text,
                        choices=[('да', 'Да'), ('нет', 'Нет')],
                        widget=forms.SelectMultiple(),
                        required=False
                    )
                    
            elif question.question_type == 'PHOTO':
                # Одиночная загрузка фото
                self.fields[field_name] = forms.ImageField(
                    label=question.question_text,
                    required=False,
                    help_text=_('Можно загрузить одно фото')
                )

    def save(self):
        """Сохраняет ответы на анкету в базу данных."""
        if self.task.client:
            client = self.task.client
        else:
            # Get the client from the form data
            client_id = self.data.get('selected_client_id')
            if not client_id:
                # Try to get from the other field name that might be used
                client_id = self.data.get('client_id')
            
            if client_id:
                try:
                    client = Client.objects.get(id=client_id)
                    # Verify that this client is assigned to the task
                    if not self.task.is_client_assigned(client.id):
                        raise ValueError(f"Клиент '{client.name}' не назначен на эту задачу")
                except Client.DoesNotExist:
                    raise ValueError("Клиент не найден")
            else:
                raise ValueError("Клиент не выбран")
        
        for question in self.task.questions.all():
            field_name = f'question_{question.id}'
            if field_name in self.cleaned_data:
                answer_data = self.cleaned_data[field_name]
                
                survey_answer = SurveyAnswer.objects.create(
                    question=question,
                    user=self.user,
                    client=client
                )
                
                if question.question_type == 'RADIO':
                    if question.choices.exists():
                        if answer_data:
                            choice = question.choices.get(id=int(answer_data))
                            survey_answer.selected_choices.add(choice)
                    else:
                        survey_answer.text_answer = answer_data
                        
                elif question.question_type == 'CHECKBOX':
                    if question.choices.exists():
                        if answer_data:
                            choices = question.choices.filter(id__in=[int(id) for id in answer_data])
                            survey_answer.selected_choices.set(choices)
                    else:
                        if isinstance(answer_data, list):
                            survey_answer.text_answer = ', '.join(answer_data)
                        else:
                            survey_answer.text_answer = answer_data or ''
                            
                elif question.question_type in ['TEXT', 'TEXT_SHORT', 'SELECT_SINGLE', 'SELECT_MULTIPLE']:
                    survey_answer.text_answer = answer_data or ''
                    
                elif question.question_type == 'PHOTO':
                    if answer_data:
                        # Сохраняем все загруженные фото
                        uploaded_files = self.files.getlist(field_name)
                        for photo_file in uploaded_files[:10]:  # Ограничение до 10 фото
                            SurveyAnswerPhoto.objects.create(
                                answer=survey_answer,
                                photo=photo_file
                            )
                survey_answer.save()
                
        # Обновляем счётчик выполненных анкет
        if self.task.task_type == 'SURVEY':
            self.task.current_count += 1
            # Проверяем, достигнут ли план
            if self.task.target_count > 0 and self.task.current_count >= self.task.target_count:
                if self.task.status != TaskStatus.COMPLETED:
                    self.task.status = TaskStatus.ON_CHECK
                # Деактивируем задачу, чтобы она исчезла из списка активных
                self.task.is_active = False
            self.task.save(update_fields=['current_count', 'status', 'is_active'])
class PhotoReportForm(forms.ModelForm):
    """Форма для заполнения фотоотчета."""
    
    photos = forms.FileField(
        label=_('Фото'),
        required=True,
        help_text=_('Загрузите фото для отчета')
    )
    
    class Meta:
        model = Task  # This will be used differently in the view
        fields = []  # We'll handle fields manually since this is for photo reports
    
    def __init__(self, *args, **kwargs):
        # Extract task from kwargs
        self.task = kwargs.pop('task', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add client name field (read-only display)
        if self.task and self.task.client:
            self.fields['client_name'] = forms.CharField(
                label=_('Название торговой точки'),
                initial=self.task.client.name,
                widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
                required=False
            )
            # Add hidden client ID field to maintain the relationship
            self.fields['client_id'] = forms.IntegerField(
                widget=forms.HiddenInput(),
                initial=self.task.client.id
            )
        elif self.task and self.task.taskclientassignment_set.exists():
            # Show only assigned clients
            assigned_client_ids = self.task.get_assigned_clients()
            assigned_clients = Client.objects.filter(id__in=assigned_client_ids)
            self.fields['client_id'] = forms.ModelChoiceField(
                queryset=assigned_clients,
                label=_('Клиент'),
                required=True
            )
        else:
            # Fallback: show autocomplete client selection for all clients
            # Add hidden field for client_id (will be filled by JavaScript)
            self.fields['client_id'] = forms.IntegerField(
                widget=forms.HiddenInput(),
                required=True
            )
        
        # Add address field
        self.fields['address'] = forms.CharField(
            label=_('Адрес'),
            widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            required=True
        )
        
        # Add stand count field
        initial_stand_count = 0
        # Get stand count from client if available
        if 'client_id' in self.fields and self.fields['client_id'].initial:
            try:
                client = Client.objects.get(id=self.fields['client_id'].initial)
                initial_stand_count = client.stand_count
            except Client.DoesNotExist:
                pass
        elif self.task and self.task.client:
            initial_stand_count = self.task.client.stand_count

        self.fields['stand_count'] = forms.IntegerField(
            label=_('Количество стендов'),
            min_value=0,
            initial=initial_stand_count,
            required=False,
            widget=forms.TextInput(attrs={
                'disabled': 'disabled',
                'maxlength': '3',
                'style': 'width: 60px;',
                'id': 'id_stand_count' # <-- Добавляем ID для удобства
            })
        )
        
        # Add comment field
        self.fields['comment'] = forms.CharField(
            label=_('Комментарий'),
            widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            required=False
        )

class AddPhotosForm(forms.Form):
    """
    Форма для добавления дополнительных фото к существующему ответу.
    """
    photos = forms.FileField(
        label=_('Дополнительные фото'),
        required=True,
        help_text=_('Можно добавить до 10 фото в общей сложности')
        # УДАЛЕНО: widget=forms.FileInput(attrs={'multiple': True})
    )
    
class AddSinglePhotoForm(forms.Form):
    """Форма для добавления одного фото к ответу."""
    photo = forms.ImageField(
        label=_('Фото'),
        required=True,
        help_text=_('Добавьте одно фото')
    )