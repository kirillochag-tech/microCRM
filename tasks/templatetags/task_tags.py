from django import template

register = template.Library()

@register.filter
def is_client_completed(task, user_id):
    """Проверяет, завершил ли пользователь задачу для клиента."""
    completed_ids = task.get_completed_client_ids_for_user(user_id)
    return list(completed_ids)