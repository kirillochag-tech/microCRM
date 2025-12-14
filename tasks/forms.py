# tasks/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _ 
from .models import SurveyAnswer, SurveyAnswerPhoto, SurveyQuestion, Client, SurveyQuestionChoice
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
                    max_length=20
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
            # Get the client from the form data (using the hidden field)
            client_id = self.data.get('selected_client_id')
            if client_id:
                try:
                    client = Client.objects.get(id=client_id)
                except Client.DoesNotExist:
                    # Fallback: try to get by name if ID is not available
                    client_name = self.data.get('selected_client', '')
                    if client_name:
                        try:
                            client = Client.objects.get(name__iexact=client_name)
                        except Client.DoesNotExist:
                            # Если точное совпадение не найдено, ищем частичное совпадение
                            try:
                                client = Client.objects.get(name__icontains=client_name)
                                # Логируем для аудита нечеткое совпадение
                                logger.warning(f"Нечеткое совпадение при поиске клиента: '{client_name}' -> '{client.name}'")
                            except Client.DoesNotExist:
                                raise ValueError(f"Клиент с названием '{client_name}' не найден")
                            except Client.MultipleObjectsReturned:
                                raise ValueError(f"Найдено несколько клиентов с названием, содержащим '{client_name}'")
                    else:
                        raise ValueError("Клиент не выбран")
            else:
                # Fallback: try to get by name if ID is not available
                client_name = self.data.get('selected_client', '')
                if client_name:
                    try:
                        client = Client.objects.get(name__iexact=client_name)
                    except Client.DoesNotExist:
                        # Если точное совпадение не найдено, ищем частичное совпадение
                        try:
                            client = Client.objects.get(name__icontains=client_name)
                            # Логируем для аудита нечеткое совпадение
                            logger.warning(f"Нечеткое совпадение при поиске клиента: '{client_name}' -> '{client.name}'")
                        except Client.DoesNotExist:
                            raise ValueError(f"Клиент с названием '{client_name}' не найден")
                        except Client.MultipleObjectsReturned:
                            raise ValueError(f"Найдено несколько клиентов с названием, содержащим '{client_name}'")
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