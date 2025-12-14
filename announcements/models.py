from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser


class AnnouncementRecipient(models.Model):
    """
    Model representing recipients for an announcement.
    
    Attributes
    ----------
    announcement : Announcement
        The announcement to which this recipient is linked
    recipient_user : CustomUser
        Individual user recipient
    """
    announcement = models.ForeignKey(
        'Announcement',
        on_delete=models.CASCADE,
        verbose_name=_('Объявление')
    )
    recipient_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )

    def __str__(self):
        return f"{self.recipient_user.username}"

    class Meta:
        verbose_name = _('Получатель объявления')
        verbose_name_plural = _('Получатели объявлений')
        unique_together = ['announcement', 'recipient_user']


class Announcement(models.Model):
    """
    Model representing an announcement message.
    
    Attributes
    ----------
    title : str
        Title of the announcement
    content : str
        Content of the announcement
    author : CustomUser
        Author of the announcement (moderator)
    created_at : datetime
        Time when the announcement was created
    requires_acknowledgment : bool
        Whether acknowledgment is required
    target_audience : str
        Who the announcement is targeted to
    recipients : ManyToManyField
        Specific recipients if target_audience is CUSTOM
    """
    
    TARGET_AUDIENCE_CHOICES = [
        ('ALL_EMPLOYEES', _('Все сотрудники')),
        ('MODERATORS', _('Модераторы')),
        ('ALL_USERS', _('Все пользователи')),
        ('CUSTOM', _('Выбранные пользователи')),
    ]
    
    title = models.CharField(_('Заголовок'), max_length=200)
    content = models.TextField(_('Содержание'))
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'MODERATOR'},
        verbose_name=_('Автор'),
        related_name='announcements'
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    requires_acknowledgment = models.BooleanField(_('Требовать подтверждения прочтения'), default=False)
    target_audience = models.CharField(
        _('Целевая аудитория'),
        max_length=20,
        choices=TARGET_AUDIENCE_CHOICES,
        default='ALL_EMPLOYEES'
    )
    recipients = models.ManyToManyField(
        CustomUser,
        through='AnnouncementRecipient',
        blank=True,
        verbose_name=_('Получатели')
    )
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = _('Объявление')
        verbose_name_plural = _('Объявления')
        ordering = ['-created_at']


class AnnouncementReadStatus(models.Model):
    """
    Model tracking read status of announcements for individual users.
    
    Attributes
    ----------
    announcement : Announcement
        The announcement that was read
    user : CustomUser
        The user who read the announcement
    read_at : datetime
        Time when the announcement was read
    acknowledged : bool
        Whether the user acknowledged reading the announcement
    """
    
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        verbose_name=_('Объявление'),
        related_name='read_statuses'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь'),
        related_name='announcement_read_statuses'
    )
    read_at = models.DateTimeField(_('Прочитано в'), auto_now_add=True)
    acknowledged = models.BooleanField(_('Подтверждено'), default=False)
    
    def __str__(self):
        status = "подтверждено" if self.acknowledged else "не подтверждено"
        return f"{self.user.username} - {self.announcement.title} ({status})"
    
    class Meta:
        verbose_name = _('Статус прочтения объявления')
        verbose_name_plural = _('Статусы прочтения объявлений')
        unique_together = ['announcement', 'user']
        ordering = ['-read_at']
