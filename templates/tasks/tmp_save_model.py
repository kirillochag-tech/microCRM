    def save_model(self, request, obj, form, change):
        """
        Кастомная логика сохранения модели с валидацией.
        """
        from django.core.exceptions import ValidationError
        
        # Получаем данные из формы
        task_type = form.cleaned_data.get('task_type')
        client = form.cleaned_data.get('client')
        assigned_to = form.cleaned_data.get('assigned_to')
        for_all_clients = form.cleaned_data.get('for_all_clients', False)
        
        # Валидация только если тип задачи выбран
        if task_type:
            # Валидация для фотоотчета по оборудованию
            if task_type == TaskType.PHOTO_REPORT:
                if not client:
                    raise ValidationError(_('Для задачи типа "Фотоотчет по оборудованию" необходимо выбрать клиента.'))
                if not assigned_to:
                    raise ValidationError(_('Для задачи типа "Фотоотчет по оборудованию" необходимо назначить сотрудника.'))
            
            # Валидация для анкеты
            if task_type == TaskType.SURVEY:
                if not for_all_clients and not client:
                    raise ValidationError(_('Для задачи типа "Анкета" необходимо либо выбрать клиента, либо отметить "Для всех клиентов".'))

        # Устанавливаем создателя задачи
        if not change:  # При создании новой задачи
            obj.created_by = request.user
            
        # Сохраняем объект
        super().save_model(request, obj, form, change)