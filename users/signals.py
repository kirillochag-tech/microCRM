from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import CustomUser

@receiver(pre_save, sender=CustomUser)
def set_staff_for_moderators(sender, instance, **kwargs):
    """Автоматически устанавливает is_staff=True для модераторов."""
    if instance.role == 'MODERATOR':
        instance.is_staff = True