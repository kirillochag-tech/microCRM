# Примеры использования API MicroCRM MCP

## Аутентификация

### Получение JWT-токена
```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin"
  }'
```

**Ответ:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzA4NjI0ODAwLCJpYXQiOjE3MDg2MjEyMDAsImp0aSI6IjEyMzQ1Njc4OTAiLCJ1c2VyX2lkIjoxfQ.abc123",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTcwOTIyNjAwMCwiaWF0IjoxNzA4NjIxMjAwLCJqdGkiOiIwOTg3NjU0MzIxIiwidXNlcl9pZCI6MX0.xyz789"
}
```

### Обновление токена
```bash
curl -X POST http://127.0.0.1:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<your_refresh_token>"
  }'
```

---

## Задачи (Tasks)

### Получение списка всех задач
```bash
curl -X GET http://127.0.0.1:8000/api/tasks/ \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
[
  {
    "id": 1,
    "title": "Фотоотчет по оборудованию",
    "description": "Сделать фотоотчет по торговому оборудованию",
    "task_type": "EQUIPMENT_PHOTO",
    "task_type_display": "Фотоотчет по оборудованию",
    "status": "SENT",
    "status_display": "В работе",
    "is_active": true,
    "created_by": 2,
    "created_at": "2026-02-20T10:00:00Z",
    "updated_at": "2026-02-20T10:00:00Z",
    "target_count": 10,
    "current_count": 5
  }
]
```

### Получение конкретной задачи
```bash
curl -X GET http://127.0.0.1:8000/api/tasks/1/ \
  -H "Authorization: Bearer <access_token>"
```

### Создание новой задачи
```bash
curl -X POST http://127.0.0.1:8000/api/tasks/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Новая анкета",
    "description": "Опрос клиентов",
    "task_type": "SURVEY",
    "target_count": 5,
    "is_active": true
  }'
```

### Обновление задачи
```bash
curl -X PATCH http://127.0.0.1:8000/api/tasks/1/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "COMPLETED",
    "is_active": false
  }'
```

### Удаление задачи
```bash
curl -X DELETE http://127.0.0.1:8000/api/tasks/1/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Клиенты (Clients)

### Получение списка всех клиентов
```bash
curl -X GET http://127.0.0.1:8000/api/clients/ \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "ИП Иванов",
    "address": "г. Москва, ул. Ленина, д. 1",
    "stand_count": 5,
    "employee": 2,
    "client_group": null,
    "created_at": "2026-02-15T09:00:00Z",
    "updated_at": "2026-02-15T09:00:00Z"
  }
]
```

### Получение конкретного клиента
```bash
curl -X GET http://127.0.0.1:8000/api/clients/1/ \
  -H "Authorization: Bearer <access_token>"
```

### Создание клиента
```bash
curl -X POST http://127.0.0.1:8000/api/clients/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ООО Ромашка",
    "address": "г. Красноярск, пр. Мира, д. 10",
    "stand_count": 3,
    "employee": 2
  }'
```

### Обновление клиента
```bash
curl -X PATCH http://127.0.0.1:8000/api/clients/1/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "stand_count": 10
  }'
```

### Удаление клиента
```bash
curl -X DELETE http://127.0.0.1:8000/api/clients/1/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Уведомления (Notifications)

### Получение списка уведомлений
```bash
curl -X GET http://127.0.0.1:8000/api/notifications/notifications/ \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
[
  {
    "id": 1,
    "recipient_username": "employee1",
    "notification_type": "TASK_ASSIGNED",
    "notification_type_display": "Назначена задача",
    "title": "Назначена задача: Фотоотчет 1",
    "message": "Вам назначена новая задача: Фотоотчет 1",
    "is_read": false,
    "created_at": "2026-02-20T10:00:00Z"
  }
]
```

### Получение конкретного уведомления
```bash
curl -X GET http://127.0.0.1:8000/api/notifications/notifications/1/ \
  -H "Authorization: Bearer <access_token>"
```

### Отметить уведомление как прочитанное
```bash
curl -X POST http://127.0.0.1:8000/api/notifications/notifications/1/read/ \
  -H "Authorization: Bearer <access_token>"
```

### Отметить все уведомления как прочитанные
```bash
curl -X POST http://127.0.0.1:8000/api/notifications/mark-all-read/ \
  -H "Authorization: Bearer <access_token>"
```

### Получить количество непрочитанных уведомлений
```bash
curl -X GET http://127.0.0.1:8000/api/notifications/unread-count/ \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
{
  "unread_count": 5
}
```

---

## Сотрудники (Employees)

### Получение списка сотрудников
```bash
curl -X GET http://127.0.0.1:8000/api/employees/ \
  -H "Authorization: Bearer <access_token>"
```

**Ответ:**
```json
[
  {
    "id": 2,
    "username": "employee1",
    "first_name": "Иван",
    "last_name": "Петров",
    "email": "employee1@example.com",
    "role": "EMPLOYEE",
    "phone": "+79991234567",
    "employee_group": null
  }
]
```

### Получение конкретного сотрудника
```bash
curl -X GET http://127.0.0.1:8000/api/employees/2/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Группы клиентов (Client Groups)

### Получение списка групп клиентов
```bash
curl -X GET http://127.0.0.1:8000/api/client-groups/ \
  -H "Authorization: Bearer <access_token>"
```

### Создание группы клиентов
```bash
curl -X POST http://127.0.0.1:8000/api/client-groups/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Группа А",
    "clients": [1, 2, 3]
  }'
```

---

## Группы сотрудников (Employee Groups)

### Получение списка групп сотрудников
```bash
curl -X GET http://127.0.0.1:8000/api/employee-groups/ \
  -H "Authorization: Bearer <access_token>"
```

### Создание группы сотрудников
```bash
curl -X POST http://127.0.0.1:8000/api/employee-groups/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Отдел продаж",
    "employees": [2, 3, 4]
  }'
```

---

## Объявления (Announcements)

### Получение списка объявлений
```bash
curl -X GET http://127.0.0.1:8000/api/announcements/ \
  -H "Authorization: Bearer <access_token>"
```

### Создание объявления
```bash
curl -X POST http://127.0.0.1:8000/api/announcements/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Важное объявление",
    "content": "Собрание в пятницу в 15:00",
    "recipient_type": "ALL",
    "require_read_confirmation": true
  }'
```

---

## Статистика и отчеты

### Получение статистики по задачам
```bash
curl -X GET http://127.0.0.1:8000/api/reports/task-statistics/ \
  -H "Authorization: Bearer <access_token>"
```

### Получение статистики по сотрудникам
```bash
curl -X GET http://127.0.0.1:8000/api/reports/employee-statistics/ \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "employee_id": 2,
    "date_from": "2026-02-01",
    "date_to": "2026-02-28"
  }'
```

---

## Фильтрация и поиск

### Фильтрация задач по статусу
```bash
curl -X GET "http://127.0.0.1:8000/api/tasks/?status=SENT" \
  -H "Authorization: Bearer <access_token>"
```

### Фильтрация задач по типу
```bash
curl -X GET "http://127.0.0.1:8000/api/tasks/?task_type=SURVEY" \
  -H "Authorization: Bearer <access_token>"
```

### Поиск клиентов по названию
```bash
curl -X GET "http://127.0.0.1:8000/api/clients/?search=ИП" \
  -H "Authorization: Bearer <access_token>"
```

### Пагинация результатов
```bash
curl -X GET "http://127.0.0.1:8000/api/tasks/?page=2&page_size=10" \
  -H "Authorization: Bearer <access_token>"
```

**Ответ с пагинацией:**
```json
{
  "count": 100,
  "next": "http://127.0.0.1:8000/api/tasks/?page=3",
  "previous": "http://127.0.0.1:8000/api/tasks/?page=1",
  "results": [
    {...},
    {...}
  ]
}
```

---

## Python примеры

### Пример использования на Python
```python
import requests

# Аутентификация
auth_response = requests.post('http://127.0.0.1:8000/api/token/', json={
    'username': 'admin',
    'password': 'admin'
})
tokens = auth_response.json()
access_token = tokens['access']

headers = {'Authorization': f'Bearer {access_token}'}

# Получение списка задач
tasks_response = requests.get('http://127.0.0.1:8000/api/tasks/', headers=headers)
tasks = tasks_response.json()
print(f"Найдено задач: {len(tasks)}")

# Создание новой задачи
new_task = requests.post('http://127.0.0.1:8000/api/tasks/', headers=headers, json={
    'title': 'Новая задача',
    'description': 'Описание задачи',
    'task_type': 'SURVEY',
    'target_count': 5
})
print(f"Создана задача ID: {new_task.json()['id']}")

# Получение уведомлений
notifications = requests.get('http://127.0.0.1:8000/api/notifications/notifications/', headers=headers)
unread = [n for n in notifications.json() if not n['is_read']]
print(f"Непрочитанных уведомлений: {len(unread)}")
```

### Пример с обработкой ошибок
```python
import requests
from requests.exceptions import HTTPError

def get_tasks(token):
    try:
        response = requests.get(
            'http://127.0.0.1:8000/api/tasks/',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            print("Ошибка аутентификации. Обновите токен.")
        elif e.response.status_code == 403:
            print("Доступ запрещен.")
        else:
            print(f"HTTP ошибка: {e}")
    except Exception as e:
        print(f"Ошибка: {e}")
    return []

# Использование
tasks = get_tasks(access_token)
```

---

## curl примеры для быстрого тестирования

```bash
# Установите токен в переменную окружения
export TOKEN="your_access_token_here"

# Получить все задачи
curl -s http://127.0.0.1:8000/api/tasks/ -H "Authorization: Bearer $TOKEN" | jq

# Получить все уведомления
curl -s http://127.0.0.1:8000/api/notifications/notifications/ -H "Authorization: Bearer $TOKEN" | jq

# Отметить все уведомления как прочитанные
curl -X POST http://127.0.0.1:8000/api/notifications/mark-all-read/ -H "Authorization: Bearer $TOKEN"

# Получить статистику
curl -s http://127.0.0.1:8000/api/reports/task-statistics/ -H "Authorization: Bearer $TOKEN" | jq
```

---

## JavaScript/Fetch примеры

```javascript
const API_BASE = 'http://127.0.0.1:8000/api';

// Аутентификация
async function authenticate(username, password) {
  const response = await fetch(`${API_BASE}/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  return await response.json();
}

// Получение задач
async function getTasks(token) {
  const response = await fetch(`${API_BASE}/tasks/`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await response.json();
}

// Отметить уведомление как прочитанное
async function markNotificationRead(token, notificationId) {
  await fetch(`${API_BASE}/notifications/notifications/${notificationId}/read/`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
}

// Пример использования
(async () => {
  const { access } = await authenticate('admin', 'admin');
  const tasks = await getTasks(access);
  console.log('Задачи:', tasks);
})();
```
