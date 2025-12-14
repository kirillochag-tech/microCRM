"""
Task management models for the employee management system.

This module defines task models, their types, and related entities.
Implements SOLID principles by separating different task types into
specialized models while maintaining a common base.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from users.models import CustomUser, UserRoles
from clients.models import Client

class TaskStatus(models.TextChoices):
    """Статусы задач."""
    DRAFT = 'DRAFT', _('Черновик')
    SENT = 'SENT', _('Отправлено')
    REWORK = 'REWORK', _('На доработку')
    ON_CHECK = 'ON_CHECK', _('На проверке')
    COMPLETED = 'COMPLETED', _('Завершена')

class TaskType(models.TextChoices):
    """Типы задач."""
    SURVEY = 'SURVEY', _('Анкета')
    EQUIPMENT_PHOTO = 'EQUIPMENT_PHOTO', _('Фотоотчет по оборудованию')
    SIMPLE_PHOTO = 'SIMPLE_PHOTO', _('Фотоотчет простой')

class Task(models.Model):
    """
    Базовая модель задачи.
    
    Атрибуты
    ----------
    title : str
        Название задачи
    description : str, optional
        Описание задачи
    task_type : str
        Тип задачи
    status : str
        Текущий статус задачи
    is_active : bool
        Активна ли задача для отображения сотрудникам
    assigned_to : CustomUser, optional
        Назначенный сотрудник
    client : Client, optional
        Клиент, связанный с задачей
    created_by : CustomUser
        Создатель задачи (модератор)
    created_at : datetime
        Время создания
    updated_at : datetime
        Время последнего обновления
    moderator_comment : str, optional
        Комментарий модератора
    target_count : int, optional
        Целевое количество ответов (для анкет)
    current_count : int
        Текущее количество ответов (для анкет)
    """
    
    title = models.CharField(_('Название задачи'), max_length=200)
    description = models.TextField(_('Описание'), blank=True, null=True)
    task_type = models.CharField(
        _('Тип задачи'),
        max_length=20,
        choices=TaskType.choices
    )
    status = models.CharField(
        _('Статус'),
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.DRAFT
    )
    is_active = models.BooleanField(_('Активная'), default=True)
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': UserRoles.EMPLOYEE},
        verbose_name=_('Назначено сотруднику')
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Клиент')
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        limit_choices_to={'role': UserRoles.MODERATOR},
        verbose_name=_('Создано модератором')
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    moderator_comment = models.TextField(
        _('Комментарий модератора'),
        blank=True,
        null=True
    )
    target_count = models.PositiveIntegerField(
        _('Целевое количество ответов'),
        default=0,
        help_text=_('Для анкет: сколько клиентов нужно опросить')
    )
    current_count = models.PositiveIntegerField(
        _('Текущее количество ответов'),
        default=0
    )
    
    def __str__(self):
        return f"{self.title} ({self.get_task_type_display()})"
    
    def can_be_viewed_by(self, user):
        """Проверяет, может ли пользователь просматривать задачу."""
        if user.role == UserRoles.MODERATOR:
            return True
        if user.role == UserRoles.EMPLOYEE:
            return (
                self.status in [TaskStatus.SENT, TaskStatus.REWORK, TaskStatus.ON_CHECK] and
                self.is_active and
                (self.assigned_to == user or self.assigned_to is None)
            )
        return False
    
    def can_be_edited_by(self, user):
        """Проверяет, может ли пользователь редактировать задачу."""
        return user.role == UserRoles.MODERATOR
    
    def get_completion_percentage(self):
        """Возвращает процент выполнения для анкет."""
        if self.task_type == TaskType.SURVEY and self.target_count > 0:
            return min(100, int((self.current_count / self.target_count) * 100))
        return 0
    
    class Meta:
        verbose_name = _('Задача')
        verbose_name_plural = _('Задачи')
        ordering = ['-created_at']

class SurveyQuestion(models.Model):
    """
    Модель вопроса для анкеты.
    
    Атрибуты
    ----------
    task : Task
        Родительская задача (только анкеты)
    question_text : str
        Текст вопроса
    order : int
        Порядок отображения
    question_type : str
        Тип вопроса
    created_at : datetime
        Время создания
    """
    
    QUESTION_TYPE_CHOICES = [
                ('TEXT', 'Текстовое поле'),
                ('TEXT_SHORT', 'Короткое текстовое поле (20 символов)'),
                ('RADIO', 'Радиокнопки (одиночный выбор)'),
                ('CHECKBOX', 'Чекбоксы (множественный выбор)'),
                ('SELECT_SINGLE', 'Выбор из списка (одиночный выбор)'),
                ('SELECT_MULTIPLE', 'Выбор из списка (множественный выбор)'),
                ('PHOTO', 'Фото'),
            ]
    
    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        limit_choices_to={'task_type': TaskType.SURVEY},
        related_name='questions',
        verbose_name=_('Задача')
    )
    question_text = models.CharField(_('Текст вопроса'), max_length=500)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    question_type = models.CharField(
        _('Тип вопроса'),
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='TEXT'
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    
    def __str__(self):
        return self.question_text[:50] + '...' if len(self.question_text) > 50 else self.question_text
    
    def has_custom_choices(self):
        """Проверяет наличие кастомных вариантов ответов."""
        return self.choices.exists()
    
    class Meta:
        verbose_name = _('Вопрос анкеты')
        verbose_name_plural = _('Вопросы анкет')
        ordering = ['order']

class SurveyQuestionChoice(models.Model):
    """
    Модель варианта ответа для вопроса.
    
    Атрибуты
    ----------
    question : SurveyQuestion
        Родительский вопрос
    choice_text : str
        Текст варианта ответа
    is_correct : bool
        Является ли правильным ответом
    order : int
        Порядок отображения
    """
    
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name=_('Вопрос')
    )
    choice_text = models.CharField(_('Текст варианта'), max_length=200)
    is_correct = models.BooleanField(_('Правильный ответ'), default=False)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    
    def __str__(self):
        return self.choice_text
    
    class Meta:
        verbose_name = _('Вариант ответа')
        verbose_name_plural = _('Варианты ответов')
        ordering = ['order']

# УДАЛИТЕ поле photo из SurveyAnswer
class SurveyAnswer(models.Model):
    """
    Survey answer model storing user responses.
    """
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('Вопрос')
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    selected_choices = models.ManyToManyField(
        SurveyQuestionChoice,
        blank=True,
        verbose_name=_('Выбранные варианты')
    )
    text_answer = models.TextField(_('Текстовый ответ'), blank=True, null=True)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name=_('Клиент')
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)

    def __str__(self):
        return f"Ответ от {self.user.username} на '{self.question.question_text[:30]}...'"
    
    class Meta:
        verbose_name = _('Ответ на вопрос')
        verbose_name_plural = _('Ответы на вопросы')

# ДОБАВЬТЕ новую модель для фото
import os
from datetime import datetime

class SurveyAnswerGroupReadStatus(models.Model):
    """
    Model to track when a group of survey answers is marked as read.
    A group is defined by task, client, user, and date.
    """
    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        verbose_name=_('Задача')
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name=_('Клиент')
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    date_created = models.DateField(_('Дата создания группы'), auto_now_add=True)
    read_at = models.DateTimeField(_('Отмечено как прочитано'), null=True, blank=True)
    read_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='read_survey_groups',
        verbose_name=_('Прочитано пользователем')
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    
    def __str__(self):
        return f"Группа: {self.task.title} - {self.client.name} - {self.user.username} ({self.date_created})"
    
    class Meta:
        verbose_name = _('Статус прочтения группы ответов')
        verbose_name_plural = _('Статусы прочтения групп ответов')
        unique_together = ['task', 'client', 'user', 'date_created']
        ordering = ['-created_at']


class SurveyAnswerPhoto(models.Model):
    """
    Multiple photos for a single survey answer.
    """
    answer = models.ForeignKey(
        SurveyAnswer,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name=_('Ответ')
    )
    photo = models.ImageField(
        _('Фото'),
        upload_to='survey_answer_photos/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        max_length=500  # Increase max_length to handle long paths
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Only modify the path if the file is being saved for the first time
        # and we have the required data
        if self.answer and self.answer.client and self.photo and hasattr(self.photo, 'name'):
            # Sanitize client name to be safe for paths (replace both forward and backslashes)
            client_name = self.answer.client.name.replace('/\\', '_').replace(' ', '_')
            # Use current datetime for path
            current_datetime = datetime.now()
            date_path = current_datetime.strftime('%Y/%m/%d')
            
            # Extract original filename safely
            original_filename = os.path.basename(self.photo.name)
            name, ext = os.path.splitext(original_filename)
            
            # Add timestamp to avoid conflicts
            timestamp = current_datetime.strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Use only first 3 digits of microseconds
            new_filename = f"{name}_{timestamp}{ext}"
            
            # Construct the new path using forward slashes only (Django handles this correctly)
            # Avoid duplication by not adding survey_answer_photos/ again since the upload_to already does this
            self.photo.name = f"survey_answer_photos/{client_name}/{date_path}/{new_filename}".replace('\\', '/')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Фото для ответа {self.answer.id}"
    
    class Meta:
        verbose_name = _('Фото ответа')
        verbose_name_plural = _('Фото ответов')
        
        
        
class SurveyPhoto(models.Model):
    """Модель для хранения нескольких фото к ответу."""
    answer = models.ForeignKey(
        SurveyAnswer,
        on_delete=models.CASCADE,
        related_name='survey_photos',
        verbose_name=_('Ответ')
    )
    photo = models.ImageField(
        _('Фото'),
        upload_to='survey_photos/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    description = models.CharField(
        _('Описание'),
        max_length=200,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    
    def __str__(self):
        return f"Фото для {self.answer.question.question_text[:30]}..."
    
    class Meta:
        verbose_name = _('Фото ответа')
        verbose_name_plural = _('Фото ответов')

class PhotoReport(models.Model):
    """
    Модель фотоотчета.
    
    Атрибуты
    ----------
    task : Task
        Родительская задача (фотоотчеты)
    client : Client
        Клиент для отчета
    address : str
        Адрес
    stand_count : int
        Количество стендов
    comment : str, optional
        Комментарий
    created_by : CustomUser
        Автор отчета
    created_at : datetime
        Время создания
    """
    
    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        limit_choices_to={
            'task_type__in': [TaskType.EQUIPMENT_PHOTO, TaskType.SIMPLE_PHOTO]
        },
        related_name='photo_reports',
        verbose_name=_('Задача')
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name=_('Клиент')
    )
    address = models.CharField(_('Адрес'), max_length=300)
    stand_count = models.PositiveIntegerField(_('Количество стендов'), default=0)
    comment = models.TextField(_('Комментарий'), blank=True, null=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('Создано')
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    
    def __str__(self):
        report_type = _("оборудованию") if self.is_equipment_report() else _("простой")
        return f"Фотоотчет ({report_type}) для {self.client.name}"
    
    def is_equipment_report(self):
        """Проверяет, является ли отчет по оборудованию."""
        return self.task.task_type == TaskType.EQUIPMENT_PHOTO
    
    def is_simple_report(self):
        """Проверяет, является ли простым отчетом."""
        return self.task.task_type == TaskType.SIMPLE_PHOTO
    
    class Meta:
        verbose_name = _('Фотоотчет')
        verbose_name_plural = _('Фотоотчеты')

class PhotoReportItem(models.Model):
    """
    Модель фотографии для отчета.
    
    Атрибуты
    ----------
    report : PhotoReport
        Родительский отчет
    photo : ImageField
        Фотография
    description : str, optional
        Описание фотографии
    quality_score : float, optional
        Оценка качества
    is_accepted : bool
        Принята ли фотография
    created_at : datetime
        Время создания
    """
    
    report = models.ForeignKey(
        PhotoReport,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name=_('Отчет')
    )
    photo = models.ImageField(
        _('Фото'),
        upload_to='photo_reports/%Y/%m/%d/'
    )
    description = models.CharField(
        _('Описание'),
        max_length=200,
        blank=True,
        null=True
    )
    quality_score = models.FloatField(
        _('Качество фото'),
        blank=True,
        null=True,
        help_text=_('Оценка качества от 0.0 до 1.0')
    )
    is_accepted = models.BooleanField(
        _('Принято'),
        default=False
    )
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    
    def __str__(self):
        return f"Фото для {self.report.client.name} ({self.created_at.date()})"
    
    class Meta:
        verbose_name = _('Фото для отчета')
        verbose_name_plural = _('Фото для отчетов')

class SurveyClientAssignment(models.Model):
    """
    Связь между анкетой и клиентом.
    
    Атрибуты
    ----------
    task : Task
        Задача-анкета
    client : Client
        Клиент
    employee : CustomUser
        Сотрудник
    completed : bool
        Завершено ли
    completed_at : datetime, optional
        Время завершения
    created_at : datetime
        Время создания
    """
    
    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        limit_choices_to={'task_type': TaskType.SURVEY},
        verbose_name=_('Задача')
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name=_('Клиент')
    )
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': UserRoles.EMPLOYEE},
        verbose_name=_('Сотрудник')
    )
    completed = models.BooleanField(_('Завершено'), default=False)
    completed_at = models.DateTimeField(_('Завершено'), null=True, blank=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    
    def __str__(self):
        return f"{self.task.title} - {self.client.name}"
    
    class Meta:
        verbose_name = _('Назначение клиента к анкете')
        verbose_name_plural = _('Назначения клиентов к анкетам')
        unique_together = ('task', 'client', 'employee')
        
# tasks/models.py - добавьте в конец файла

class TaskStatistics(models.Model):
    """
    Модель для хранения агрегированной статистики по задачам.
    Используется для создания отчетов и дашбордов.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_statistics_tasks')
    total_responses = models.PositiveIntegerField(_('Всего ответов'), default=0)
    unique_clients = models.PositiveIntegerField(_('Уникальных клиентов'), default=0)
    completion_rate = models.FloatField(_('Процент выполнения'), default=0.0)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлено'), auto_now=True)
    
    class Meta:
        verbose_name = _('Статистика задачи')
        verbose_name_plural = _('Статистика задач')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Статистика: {self.task.title}"
