(function() {
    'use strict';
    
    // Храним оригинальные опции для восстановления
    const originalOptions = {
        employee: null,
        client: null
    };
    
    // Храним текущие назначения перед применением группового фильтра
    const savedAssignments = {
        employee: null,
        client: null
    };
    
    // Функция для получения оригинальных опций
    function getOriginalOptions(groupName, fromElement) {
        if (originalOptions[groupName] === null) {
            originalOptions[groupName] = Array.from(fromElement.options);
        }
        return originalOptions[groupName];
    }
    
    // Функция для ручного обновления DOM списков
    function updateFilterDOM(fromElement, toElement) {
        // Сохраняем текущее выделение в правом поле
        const previouslySelectedValues = Array.from(toElement.selectedOptions).map(opt => opt.value);
        
        // Очищаем текущие опции
        fromElement.innerHTML = '';
        toElement.innerHTML = '';
        
        // Восстанавливаем опции из кэша SelectBox
        if (typeof SelectBox !== 'undefined') {
            // Левое поле (доступные)
            const fromCache = SelectBox.cache[fromElement.id] || [];
            fromCache.forEach(option => {
                const opt = document.createElement('option');
                opt.value = option.value;
                opt.textContent = option.text;
                fromElement.appendChild(opt);
            });
            
            // Правое поле (выбранные)
            const toCache = SelectBox.cache[toElement.id] || [];
            toCache.forEach(option => {
                const opt = document.createElement('option');
                opt.value = option.value;
                opt.textContent = option.text;
                // Восстанавливаем предыдущее выделение
                if (previouslySelectedValues.includes(option.value)) {
                    opt.selected = true;
                }
                toElement.appendChild(opt);
            });
        }
        
        // Принудительно вызываем события изменения
        const fromEvent = new Event('change', { bubbles: true });
        const toEvent = new Event('change', { bubbles: true });
        fromElement.dispatchEvent(fromEvent);
        toElement.dispatchEvent(toEvent);
    }
    
    // Функция сброса конкретного селектора группы
    function resetGroupSelector(groupName) {
        if (groupName === 'employee') {
            const employeeGroupSelect = document.getElementById('id_employee_group');
            if (employeeGroupSelect) {
                employeeGroupSelect.value = '';
            }
        } else if (groupName === 'client') {
            const clientGroupSelect = document.getElementById('id_client_group');
            if (clientGroupSelect) {
                clientGroupSelect.value = '';
            }
        }
    }
    
    // Функция для добавления выбранных элементов из левого поля в правое
    function addSelectedToRight(fromElement, toElement, groupName) {
        const selectedOptions = Array.from(fromElement.selectedOptions);
        
        if (selectedOptions.length === 0) return;
        
        // Получаем текущие кэши
        const fromCache = SelectBox.cache[fromElement.id] || [];
        const toCache = SelectBox.cache[toElement.id] || [];
        
        // Создаем Map для быстрого поиска
        const toCacheMap = new Map(toCache.map(opt => [opt.value, opt]));
        
        // Перемещаем выбранные опции
        const newFromCache = [];
        const newToCache = [...toCache]; // Копируем существующие
        
        fromCache.forEach(opt => {
            const isSelected = selectedOptions.some(selectedOpt => selectedOpt.value === opt.value);
            if (isSelected) {
                // Добавляем в правое поле, если ещё не там
                if (!toCacheMap.has(opt.value)) {
                    newToCache.push(opt);
                }
            } else {
                newFromCache.push(opt);
            }
        });
        
        // Обновляем кэши
        SelectBox.cache[fromElement.id] = newFromCache;
        SelectBox.cache[toElement.id] = newToCache;
        
        // Сбрасываем селектор группы при ручном изменении
        resetGroupSelector(groupName);
        
        // Обновляем DOM
        updateFilterDOM(fromElement, toElement);
    }
    
    // Функция для удаления конкретного элемента из правого поля в левое
    function removeSpecificFromRight(fromElement, toElement, optionValue, groupName) {
        // Получаем текущие кэши
        const fromCache = SelectBox.cache[fromElement.id] || [];
        const toCache = SelectBox.cache[toElement.id] || [];
        
        // Создаем Map для быстрого поиска
        const fromCacheMap = new Map(fromCache.map(opt => [opt.value, opt]));
        
        // Перемещаем конкретную опцию обратно
        const newFromCache = [...fromCache];
        const newToCache = [];
        
        let foundOption = null;
        toCache.forEach(opt => {
            if (opt.value === optionValue) {
                foundOption = opt;
            } else {
                newToCache.push(opt);
            }
        });
        
        // Добавляем найденную опцию в левое поле, если она существует
        if (foundOption && !fromCacheMap.has(foundOption.value)) {
            newFromCache.push(foundOption);
        }
        
        // Обновляем кэши
        SelectBox.cache[fromElement.id] = newFromCache;
        SelectBox.cache[toElement.id] = newToCache;
        
        // Сбрасываем селектор группы при ручном изменении
        resetGroupSelector(groupName);
        
        // Обновляем DOM
        updateFilterDOM(fromElement, toElement);
    }
    
    // Функция для удаления всех элементов из правого поля
    function removeAllFromRight(fromElement, toElement, groupName) {
        const toCache = SelectBox.cache[toElement.id] || [];
        const fromCache = SelectBox.cache[fromElement.id] || [];
        
        // Объединяем все опции
        const combinedCache = [...fromCache, ...toCache];
        
        // Удаляем дубликаты
        const uniqueCache = [];
        const seen = new Set();
        combinedCache.forEach(opt => {
            if (!seen.has(opt.value)) {
                seen.add(opt.value);
                uniqueCache.push(opt);
            }
        });
        
        // Обновляем кэши
        SelectBox.cache[fromElement.id] = uniqueCache;
        SelectBox.cache[toElement.id] = [];
        
        // Сбрасываем селектор группы при удалении всех
        resetGroupSelector(groupName);
        
        // Обновляем DOM
        updateFilterDOM(fromElement, toElement);
    }
    
    // Функция для добавления всех элементов из левого поля в правое
    function addAllToRight(fromElement, toElement, groupName) {
        const fromCache = SelectBox.cache[fromElement.id] || [];
        const toCache = SelectBox.cache[toElement.id] || [];
        
        // Объединяем без дубликатов
        const toCacheMap = new Map(toCache.map(opt => [opt.value, opt]));
        const newToCache = [...toCache];
        
        fromCache.forEach(opt => {
            if (!toCacheMap.has(opt.value)) {
                newToCache.push(opt);
            }
        });
        
        // Обновляем кэши
        SelectBox.cache[fromElement.id] = [];
        SelectBox.cache[toElement.id] = newToCache;
        
        // Сбрасываем селектор группы при выборе всех
        resetGroupSelector(groupName);
        
        // Обновляем DOM
        updateFilterDOM(fromElement, toElement);
    }
    
    // Функция для установки обработчиков ручного выбора
    function setupManualSelectionHandlers(filterFromElement, filterToElement, groupName) {
        // Отключаем стандартные обработчики
        const moveAllRight = document.querySelector('.selector-available .selector-chooseall');
        const moveRight = document.querySelector('.selector-available .selector-add');
        const moveLeft = document.querySelector('.selector-chosen .selector-remove');
        const moveAllLeft = document.querySelector('.selector-chosen .selector-clearall');
        
        // Удаляем стандартные обработчики
        if (moveRight) moveRight.onclick = null;
        if (moveAllRight) moveAllRight.onclick = null;
        if (moveLeft) moveLeft.onclick = null;
        if (moveAllLeft) moveAllLeft.onclick = null;
        
        // Устанавливаем кастомные обработчики
        if (moveRight) {
            moveRight.addEventListener('click', function(e) {
                e.preventDefault();
                addSelectedToRight(filterFromElement, filterToElement, groupName);
            });
        }
        
        if (moveAllRight) {
            moveAllRight.addEventListener('click', function(e) {
                e.preventDefault();
                addAllToRight(filterFromElement, filterToElement, groupName);
            });
        }
        
        if (moveLeft) {
            moveLeft.addEventListener('click', function(e) {
                e.preventDefault();
                const selectedOptions = Array.from(filterToElement.selectedOptions);
                if (selectedOptions.length > 0) {
                    // Удаляем только выбранные опции
                    const selectedValues = selectedOptions.map(opt => opt.value);
                    const fromCache = SelectBox.cache[filterFromElement.id] || [];
                    const toCache = SelectBox.cache[filterToElement.id] || [];
                    
                    const fromCacheMap = new Map(fromCache.map(opt => [opt.value, opt]));
                    const newFromCache = [...fromCache];
                    const newToCache = [];
                    
                    toCache.forEach(opt => {
                        if (selectedValues.includes(opt.value)) {
                            if (!fromCacheMap.has(opt.value)) {
                                newFromCache.push(opt);
                            }
                        } else {
                            newToCache.push(opt);
                        }
                    });
                    
                    SelectBox.cache[filterFromElement.id] = newFromCache;
                    SelectBox.cache[filterToElement.id] = newToCache;
                    
                    // Сбрасываем селектор группы при удалении выбранных
                    resetGroupSelector(groupName);
                    
                    updateFilterDOM(filterFromElement, filterToElement);
                }
            });
        }
        
        if (moveAllLeft) {
            moveAllLeft.style.display = ''; // Возвращаем видимость кнопки
            moveAllLeft.addEventListener('click', function(e) {
                e.preventDefault();
                removeAllFromRight(filterFromElement, filterToElement, groupName);
            });
        }
        
        // Обработка двойного клика на левом поле
        filterFromElement.addEventListener('dblclick', function(e) {
            if (e.target.tagName === 'OPTION') {
                addSelectedToRight(filterFromElement, filterToElement, groupName);
            }
        });
        
        // Обработка двойного клика на правом поле (удаление)
        filterToElement.addEventListener('dblclick', function(e) {
            if (e.target.tagName === 'OPTION') {
                removeSpecificFromRight(filterFromElement, filterToElement, e.target.value, groupName);
            }
        });
    }
    
    // Функция сброса селекторов групп при сохранении
    function resetGroupSelectorsOnSave() {
        const employeeGroupSelect = document.getElementById('id_employee_group');
        const clientGroupSelect = document.getElementById('id_client_group');
        
        if (employeeGroupSelect) {
            employeeGroupSelect.value = '';
        }
        if (clientGroupSelect) {
            clientGroupSelect.value = '';
        }
    }
    
    // Функция установки обработчика на кнопку сохранения
    function setupSaveButtonHandler() {
        // Находим все кнопки сохранения
        const saveButtons = document.querySelectorAll('input[name="_save"], input[name="_continue"], input[name="_addanother"]');
        
        saveButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Сбрасываем селекторы групп перед отправкой формы
                resetGroupSelectorsOnSave();
            });
        });
    }
    
    // ОСНОВНАЯ ФУНКЦИЯ: переместить всех членов группы в правое окно
    function moveGroupMembersToRight(groupSelect, filterFromElement, filterToElement, groupName) {
        const groupId = groupSelect.value;
        
        if (!groupId || groupId === '') {
            // Сохраняем текущие назначения перед сбросом
            savedAssignments[groupName] = [...(SelectBox.cache[filterToElement.id] || [])];
            
            // Восстанавливаем оригинальный список в левом поле
            const originalOpts = getOriginalOptions(groupName, filterFromElement);
            SelectBox.cache[filterFromElement.id] = originalOpts.map(opt => ({
                value: opt.value,
                text: opt.textContent
            }));
            
            // Восстанавливаем сохраненные назначения в правом поле
            SelectBox.cache[filterToElement.id] = savedAssignments[groupName] || [];
            
            updateFilterDOM(filterFromElement, filterToElement);
            return;
        }
        
        // Сохраняем текущие назначения перед применением группового фильтра
        savedAssignments[groupName] = [...(SelectBox.cache[filterToElement.id] || [])];
        
        // Показываем индикатор загрузки
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'group-loading';
        loadingIndicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #4CAF50;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;
        loadingIndicator.textContent = 'Загрузка членов группы...';
        document.body.appendChild(loadingIndicator);
        
        fetch(`/tasks/api/${groupName}-group/${groupId}/${groupName}s/`)
            .then(response => response.json())
            .then(data => {
                const members = groupName === 'employee' ? data.employees : data.clients;
                
                console.log(`[DEBUG] Received ${members?.length || 0} ${groupName}(s) from API:`, members);
                
                if (members && members.length > 0) {
                    if (typeof SelectBox !== 'undefined') {
                        // Создаем Set для быстрого поиска
                        const memberIds = new Set(members.map(member => String(member.id)));
                        
                        // Получаем оригинальные опции
                        const originalOpts = getOriginalOptions(groupName, filterFromElement);
                        
                        // Отладка: проверяем соответствие ID
                        console.log(`[DEBUG] Original ${groupName} options count:`, originalOpts.length);
                        console.log(`[DEBUG] Member IDs from API:`, Array.from(memberIds));
                        
                        // Проверяем, какие ID из API найдены в опциях
                        const foundIds = [];
                        originalOpts.forEach(option => {
                            if (memberIds.has(option.value)) {
                                foundIds.push(option.value);
                            }
                        });
                        
                        console.log(`[DEBUG] Found matching IDs:`, foundIds);
                        
                        // Преобразуем оригинальные опции в формат кэша
                        const originalCache = originalOpts.map(opt => ({
                            value: opt.value,
                            text: opt.textContent
                        }));
                        
                        // Выбираем членов группы
                        const groupMembers = originalCache.filter(opt => memberIds.has(opt.value));
                        
                        // Объединяем членов группы с предыдущими назначениями (без дубликатов)
                        const combinedSelected = [...groupMembers];
                        const combinedMap = new Map(groupMembers.map(opt => [opt.value, opt]));
                        
                        const previousAssignments = savedAssignments[groupName] || [];
                        previousAssignments.forEach(opt => {
                            if (!combinedMap.has(opt.value)) {
                                combinedSelected.push(opt);
                            }
                        });
                        
                        // Доступные опции - всё, что не в объединенном списке
                        const availableCache = originalCache.filter(opt => !combinedMap.has(opt.value));
                        const selectedCache = combinedSelected;
                        
                        // Обновляем кэши напрямую
                        SelectBox.cache[filterFromElement.id] = availableCache;
                        SelectBox.cache[filterToElement.id] = selectedCache;
                        
                        // Обновляем DOM
                        updateFilterDOM(filterFromElement, filterToElement);
                        
                        console.log(`[DEBUG] Moved ${selectedCache.length} ${groupName}(s) from group ${groupId} to right panel`);
                        console.log(`[DEBUG] Cache after manual update - From: ${availableCache.length}, To: ${selectedCache.length}`);
                    }
                }
            })
            .catch(error => {
                console.error(`Error loading ${groupName} group:`, error);
                alert(`Ошибка загрузки: ${error.message}`);
            })
            .finally(() => {
                // Удаляем индикатор загрузки
                const indicator = document.querySelector('.group-loading');
                if (indicator) {
                    indicator.remove();
                }
            });
    }
    
    // Функция установки обработчика на селектор группы
    function setupGroupMoveHandler(groupSelect, filterFromElement, filterToElement, groupName) {
        if (!groupSelect || !filterFromElement || !filterToElement) return;
        
        // Устанавливаем обработчики ручного выбора
        setupManualSelectionHandlers(filterFromElement, filterToElement, groupName);
        
        groupSelect.addEventListener('change', function() {
            moveGroupMembersToRight(groupSelect, filterFromElement, filterToElement, groupName);
        });
    }
    
    // Функция инициализации после появления элементов
    function initializeWhenElementsReady() {
        const employeeGroupSelect = document.getElementById('id_employee_group');
        const clientGroupSelect = document.getElementById('id_client_group');
        const employeeFilterFrom = document.querySelector('#id_assigned_employees_from');
        const employeeFilterTo = document.querySelector('#id_assigned_employees_to');
        const clientFilterFrom = document.querySelector('#id_assigned_clients_from');
        const clientFilterTo = document.querySelector('#id_assigned_clients_to');
        
        const elementsFound = {
            employeeGroupSelect: !!employeeGroupSelect,
            clientGroupSelect: !!clientGroupSelect,
            employeeFilterFrom: !!employeeFilterFrom,
            employeeFilterTo: !!employeeFilterTo,
            clientFilterFrom: !!clientFilterFrom,
            clientFilterTo: !!clientFilterTo,
        };
        
        console.log('[DEBUG] Elements check:', elementsFound);
        
        // Проверяем, все ли элементы найдены
        if (employeeFilterFrom && employeeFilterTo && clientFilterFrom && clientFilterTo) {
            // Инициализация для сотрудников
            if (employeeGroupSelect) {
                setupGroupMoveHandler(employeeGroupSelect, employeeFilterFrom, employeeFilterTo, 'employee');
            }
            
            // Инициализация для клиентов
            if (clientGroupSelect) {
                setupGroupMoveHandler(clientGroupSelect, clientFilterFrom, clientFilterTo, 'client');
            }
            
            // Устанавливаем обработчик кнопок сохранения
            setupSaveButtonHandler();
            
            console.log('Task admin JavaScript initialized successfully');
            return true;
        }
        
        return false;
    }
    
    // Основная функция запуска
    function startInitialization() {
        // Сначала пробуем сразу
        if (initializeWhenElementsReady()) {
            return;
        }
        
        // Если элементы не найдены, используем MutationObserver
        const observer = new MutationObserver(function(mutations) {
            if (initializeWhenElementsReady()) {
                observer.disconnect();
            }
        });
        
        // Наблюдаем за изменениями в body
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Также устанавливаем таймаут на случай, если MutationObserver не сработает
        setTimeout(() => {
            if (!initializeWhenElementsReady()) {
                console.warn('[DEBUG] Elements not found after timeout, trying one more time');
                initializeWhenElementsReady();
            }
            observer.disconnect();
        }, 5000);
    }
    
    // Запускаем инициализацию
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startInitialization);
    } else {
        startInitialization();
    }
})();