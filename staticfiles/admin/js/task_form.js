/**
 * Динамическая логика формы создания/редактирования задачи
 * 
 * Функциональность:
 * 1. Для типа "Анкета": показывает чекбокс "Для всех клиентов"
 * 2. Для типа "Фотоотчет по оборудованию": делает клиента и сотрудника обязательными
 * 3. Управляет видимостью и обязательностью полей в зависимости от типа задачи
 * 4. Поддерживает назначение по группам
 */

(function($) {
    'use strict';

    // Константы типов задач
    const TASK_TYPES = {
        SURVEY: 'SURVEY',
        PHOTO_REPORT: 'PHOTO_REPORT'
    };

    /**
     * Инициализирует динамическую логику формы задачи
     */
    function initTaskForm() {
        const taskTypeField = $('#id_task_type');
        const clientField = $('#id_client');
        const assignedToField = $('#id_assigned_to');
        const forAllClientsCheckbox = $('#id_for_all_clients');
        const clientGroupField = $('#id_client_group');
        const employeeGroupField = $('#id_employee_group');

        // Функция обновления состояния формы в зависимости от типа задачи
        function updateFormState() {
            const selectedTaskType = taskTypeField.val();

            if (selectedTaskType === TASK_TYPES.SURVEY) {
                // Анкета: показываем чекбокс "Для всех клиентов" и поля групп
                forAllClientsCheckbox.closest('.form-row').show();
                clientGroupField.closest('.form-row').show();
                employeeGroupField.closest('.form-row').show();
                const isForAllClients = forAllClientsCheckbox.is(':checked');
                
                // Если "Для всех клиентов" отмечен, клиент не обязателен
                clientField.prop('required', !isForAllClients);
                clientField.closest('.form-row').toggleClass('required', !isForAllClients);
                assignedToField.prop('required', false);
                assignedToField.closest('.form-row').removeClass('required');
                
            } else if (selectedTaskType === TASK_TYPES.PHOTO_REPORT) {
                // Фотоотчет: скрываем чекбокс "Для всех клиентов" и поля групп
                forAllClientsCheckbox.closest('.form-row').hide();
                forAllClientsCheckbox.prop('checked', false);
                clientGroupField.closest('.form-row').hide();
                employeeGroupField.closest('.form-row').hide();
                
                // Делаем клиента и сотрудника обязательными
                clientField.prop('required', true);
                clientField.closest('.form-row').addClass('required');
                assignedToField.prop('required', true);
                assignedToField.closest('.form-row').addClass('required');
                
            } else {
                // Другие типы задач
                forAllClientsCheckbox.closest('.form-row').hide();
                forAllClientsCheckbox.prop('checked', false);
                clientGroupField.closest('.form-row').hide();
                employeeGroupField.closest('.form-row').hide();
                clientField.prop('required', false);
                clientField.closest('.form-row').removeClass('required');
                assignedToField.prop('required', false);
                assignedToField.closest('.form-row').removeClass('required');
            }
        }

        // Инициализация при загрузке страницы
        if (taskTypeField.length && clientField.length && assignedToField.length) {
            updateFormState();
            
            // Обработчик изменения типа задачи
            taskTypeField.on('change', updateFormState);
            
            // Обработчик изменения чекбокса "Для всех клиентов"
            forAllClientsCheckbox.on('change', updateFormState);
        }
    }

    // Запускаем инициализацию после загрузки DOM
    $(document).ready(function() {
        initTaskForm();
    });

    // Также запускаем после загрузки через AJAX (для админки Django)
    $(document).on('formset:added formset:removed', initTaskForm);

})(django.jQuery);