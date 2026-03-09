from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html

# Customize the admin site header
admin.site.site_header = _("microCRM")
admin.site.site_title = _("microCRM")
admin.site.index_title = _("Администрирование microCRM")

# Кастомизация главной страницы админки для группировки моделей
def get_app_list(self, request):
    app_dict = self._build_app_dict(request)
    
    # Группируем модели по нашим правилам
    ordered_app_list = []
    
    # Сначала добавляем группу "Пользователи и группы"
    users_group = {
        'name': _('Пользователи и группы'),
        'app_label': 'users_group',
        'has_module_perms': True,
        'models': [],
    }
    
    # Добавляем модели из auth в эту группу
    auth_app = app_dict.get('auth')
    if auth_app:
        for model in auth_app.get('models', []):
            model_name = model.get('verbose_name_plural', model.get('name', ''))
            # Добавляем только пользователей и группы в эту группу
            if model_name in [_('Users'), _('Пользователи'), 'Users', _('Groups'), _('Группы'), 'Groups']:
                users_group['models'].append(model)
    
    # Если есть модели в группе пользователей, добавляем её в список
    if users_group['models']:
        users_group['name'] = _('Пользователи и группы')
        users_group['app_label'] = 'users_group'
        ordered_app_list.append(users_group)
    
    # Затем добавляем остальные приложения
    for app_key in ['tasks', 'announcements', 'reports', 'clients']:
        if app_key in app_dict:
            app = app_dict[app_key]
            
            # Для приложения tasks скрываем ненужные модели
            if app_key == 'tasks':
                # Переименовываем приложение в "Задачи"
                app['name'] = _('Задачи')
                
                # Фильтруем модели, исключая нежелательные
                filtered_models = []
                for model in app.get('models', []):
                    model_verbose_name = model.get('verbose_name_plural', model.get('name', ''))
                    # Проверяем по точным именам моделей, которые должны быть скрыты
                    if model_verbose_name not in [_('Варианты ответов'), _('Фото ответов'), _('Фото для отчетов')]:
                        filtered_models.append(model)
                
                app['models'] = filtered_models
            
            ordered_app_list.append(app)
    
    return ordered_app_list

# Применяем кастомную логику к стандартному AdminSite
original_get_app_list = admin.AdminSite.get_app_list
admin.AdminSite.get_app_list = get_app_list