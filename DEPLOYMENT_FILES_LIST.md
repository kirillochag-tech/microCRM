# Список файлов для замены на рабочем проекте

## Дата: 9 марта 2026 г.
## Ветка: feature/1c-client-import

---

## 1. Основные файлы моделей и админки

### clients/models.py
**Изменения:**
- Добавлено поле `code_1c` (CharField, unique, db_index)
- Добавлены методы `get_task_count()` и `get_completed_task_count()`
- Добавлен индекс на поле `code_1c` в Meta.indexes

**Критично:** ⚠️ ДА - требует миграции

---

### clients/admin.py
**Изменения:**
- Полностью переписан класс `ClientResource` с новой логикой импорта
- **Порядок полей:** `id`, `code_1c`, `name`, `employee_username`, ... (code_1c вторым)
- Добавлен класс `ClientImportForm`
- Полностью переписан класс `ClientAdmin` с методами:
  - `get_urls()` - новые URL для импорта
  - `import_preview()` - предпросмотр импорта
  - `import_confirm()` - подтверждение импорта
- Добавлены методы `get_groups()` и `get_task_count_display()`
- Обновлен `get_search_results()` для поиска по code_1c

**Критично:** ⚠️ ДА - новый функционал

---

### tasks/models.py
**Изменения:**
- В поле `client` модели `Task` добавлен параметр `related_name='tasks'`

**Критично:** ⚠️ ДА - требует миграции

---

## 2. Шаблоны админки

### templates/admin/clients/client_import_change_list.html
**Изменения:**
- Новый файл
- Добавляет кнопку импорта Excel в список клиентов
- Форма загрузки файла с кнопкой "Импорт из 1С (Excel)"

**Критично:** ✅ НЕТ - новый файл

---

### templates/admin/clients/import_preview.html
**Изменения:**
- Новый файл
- Шаблон предварительного просмотра импорта
- Отображает:
  - Обновляемые клиенты
  - Пропущенные записи
  - Дубликаты
  - Кнопки подтверждения/отмены

**Критично:** ✅ НЕТ - новый файл

---

## 3. Миграции

### clients/migrations/0005_client_code_1c_client_clients_cli_code_1c_5f1b8a_idx.py
**Изменения:**
- Новый файл
- Добавляет поле `code_1c` в модель Client
- Создает индекс по полю `code_1c`

**Критично:** ⚠️ ДА - обязательная миграция

---

### tasks/migrations/0022_alter_task_client.py
**Изменения:**
- Новый файл
- Изменяет поле `client` модели `Task`
- Добавляет `related_name='tasks'`

**Критично:** ⚠️ ДА - обязательная миграция

---

## 4. Тесты и утилиты (НЕ требуются на продакшене)

### clients/tests_1c_import.py
**Назначение:** Тесты функционала импорта
**Копировать:** ❌ НЕТ (только для разработки)

---

### clients/management/commands/create_test_clients_for_import.py
**Назначение:** Создание тестовых клиентов
**Копировать:** ❌ НЕТ (только для разработки)

---

### clients/management/commands/create_test_excel_file.py
**Назначение:** Создание тестового Excel-файла
**Копировать:** ❌ НЕТ (только для разработки)

---

### test_import_clients.xlsx
**Назначение:** Тестовый Excel-файл
**Копировать:** ❌ НЕТ (только для разработки)

---

## 5. Документация (опционально)

### 1C_IMPORT_DOCUMENTATION.md
**Назначение:** Полная документация по импорту
**Копировать:** ✅ ОПЦИОНАЛЬНО (для справки)

---

## Инструкция по развертыванию

### Шаг 1: Резервное копирование
```bash
# Сделать бэкап базы данных
cp db.sqlite3 db.sqlite3.backup

# Сделать бэкап текущих файлов
cp clients/models.py clients/models.py.backup
cp clients/admin.py clients/admin.py.backup
cp tasks/models.py tasks/models.py.backup
```

### Шаг 2: Копирование файлов
Скопируйте следующие файлы из ветки feature/1c-client-import:

```
✅ clients/models.py
✅ clients/admin.py
✅ tasks/models.py
✅ templates/admin/clients/client_import_change_list.html
✅ templates/admin/clients/import_preview.html
✅ clients/migrations/0005_client_code_1c_client_clients_cli_code_1c_5f1b8a_idx.py
✅ tasks/migrations/0022_alter_task_client.py
```

### Шаг 3: Применение миграций
```bash
python manage.py migrate clients
python manage.py migrate tasks
```

### Шаг 4: Проверка работоспособности
```bash
# Запуск сервера
python manage.py runserver

# Проверка в админке:
# 1. Войти как модератор
# 2. Перейти в раздел "Клиенты"
# 3. Убедиться, что видна кнопка "Импорт из 1С (Excel)"
# 4. Проверить отображение поля "Код 1С" в списке клиентов
```

### Шаг 5: Создание суперпользователя (если нужно)
```bash
python manage.py createsuperuser
```

---

## Проверка после развертывания

### Чек-лист:

- [ ] Поле "Код 1С" отображается в списке клиентов
- [ ] Поле "Код 1С" отображается в форме редактирования клиента
- [ ] Кнопка "Импорт из 1С (Excel)" видна в админке
- [ ] Загрузка Excel-файла работает
- [ ] Предварительный просмотр импорта отображается
- [ ] Импорт применяет изменения корректно
- [ ] Задачи сохраняются за клиентами при обновлении
- [ ] Уникальность кода 1С проверяется
- [ ] Поиск клиентов работает по коду 1С

---

## Откат изменений (при необходимости)

```bash
# Вернуть файлы из бэкапа
cp clients/models.py.backup clients/models.py
cp clients/admin.py.backup clients/admin.py
cp tasks/models.py.backup tasks/models.py

# Отменить миграции
python manage.py migrate clients 0004
python manage.py migrate tasks 0021

# Перезапустить сервер
```

---

## Контакты для поддержки

При возникновении проблем обратитесь к разработчику или проверьте документацию:
- `1C_IMPORT_DOCUMENTATION.md` - полная документация по импорту
- `clients/tests_1c_import.py` - тесты для проверки функционала
