# -*- coding: utf-8 -*-
"""
Management command to create test clients for 1C import testing.

Creates clients with various configurations:
- With 1C code
- Without 1C code
- With tasks assigned
"""

import sys
import io
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from clients.models import Client, ClientGroup
from tasks.models import Task, TaskType, TaskStatus
from users.models import CustomUser, UserRoles, EmployeeGroup

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CustomUser = get_user_model()


class Command(BaseCommand):
    help = 'Создание тестовых клиентов для тестирования импорта из 1С'

    def handle(self, *args, **options):
        self.stdout.write('Создание тестовых клиентов для импорта из 1С...\n')

        # Создаем тестового модератора
        moderator, _ = CustomUser.objects.get_or_create(
            username='test_moderator',
            defaults={
                'email': 'moderator@test.com',
                'role': UserRoles.MODERATOR,
                'is_staff': True,
            }
        )
        moderator.set_password('test123')
        moderator.save()
        self.stdout.write(self.style.SUCCESS(f'[OK] Создан модератор: {moderator.username}'))

        # Создаем тестового сотрудника
        employee, _ = CustomUser.objects.get_or_create(
            username='test_employee',
            defaults={
                'email': 'employee@test.com',
                'role': UserRoles.EMPLOYEE,
            }
        )
        employee.set_password('test123')
        employee.save()
        self.stdout.write(self.style.SUCCESS(f'[OK] Создан сотрудник: {employee.username}'))

        # Создаем группы клиентов
        group_a, _ = ClientGroup.objects.get_or_create(
            name='Тестовая группа А',
            defaults={'description': 'Группа для тестирования импорта'}
        )
        group_b, _ = ClientGroup.objects.get_or_create(
            name='Тестовая группа Б',
            defaults={'description': 'Вторая группа для тестирования'}
        )
        self.stdout.write(self.style.SUCCESS('[OK] Созданы группы клиентов'))

        # Создаем тестовых клиентов

        # 1. Клиент с кодом 1С (будет обновлен по коду при импорте)
        client_with_code, _ = Client.objects.get_or_create(
            code_1c='1C-001',
            defaults={
                'name': 'ООО "Старое Название"',
                'employee': employee,
                'address': 'ул. Тестовая, д. 1',
                'trading_point_name': 'Торговая точка 1',
                'stand_count': 5,
            }
        )
        client_with_code.client_groups.add(group_a)
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Клиент с кодом 1С: {client_with_code.name} (код: {client_with_code.code_1c})'
        ))

        # 2. Клиент без кода 1С (будет обновлен по имени при импорте)
        client_without_code, _ = Client.objects.get_or_create(
            name='ООО "Вектор"',
            defaults={
                'employee': employee,
                'address': 'ул. Примерная, д. 10',
                'trading_point_name': 'Вектор-Маркет',
                'stand_count': 3,
            }
        )
        client_without_code.client_groups.add(group_b)
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Клиент без кода 1С: {client_without_code.name}'
        ))

        # 3. Клиент с кодом 1С и задачами (для проверки сохранения задач)
        client_with_tasks, _ = Client.objects.get_or_create(
            code_1c='1C-002',
            defaults={
                'name': 'ИП Петров',
                'employee': employee,
                'address': 'пр. Ленина, д. 50',
                'stand_count': 2,
            }
        )
        client_with_tasks.client_groups.add(group_a)
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Клиент с задачами: {client_with_tasks.name} (код: {client_with_tasks.code_1c})'
        ))

        # Создаем тестовые задачи для клиента
        task1, _ = Task.objects.get_or_create(
            title=f'Анкета для {client_with_tasks.name}',
            defaults={
                'description': 'Тестовая анкета',
                'task_type': TaskType.SURVEY,
                'status': TaskStatus.SENT,
                'created_by': moderator,
                'client': client_with_tasks,
                'target_count': 10,
                'current_count': 3,
            }
        )
        
        task2, _ = Task.objects.get_or_create(
            title=f'Фотоотчет для {client_with_tasks.name}',
            defaults={
                'description': 'Тестовый фотоотчет',
                'task_type': TaskType.EQUIPMENT_PHOTO,
                'status': TaskStatus.ON_CHECK,
                'created_by': moderator,
                'client': client_with_tasks,
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Создано задач для клиента: {client_with_tasks.get_task_count()}'
        ))

        # 4. Клиент для проверки дублей (с таким же именем будет в импорте)
        client_for_duplicate_test, _ = Client.objects.get_or_create(
            name='ООО "Альфа"',
            defaults={
                'code_1c': '1C-003',
                'employee': employee,
                'address': 'ул. Мира, д. 25',
                'stand_count': 4,
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Клиент для теста дублей: {client_for_duplicate_test.name}'
        ))

        # 5. Клиент только с именем (для проверки пропуска при импорте)
        client_name_only, _ = Client.objects.get_or_create(
            name='ООО "Бета"',
            defaults={
                'employee': employee,
                'address': 'пер. Короткий, д. 3',
                'stand_count': 1,
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Клиент только с именем: {client_name_only.name}'
        ))

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('[OK] Все тестовые клиенты созданы!'))
        self.stdout.write('=' * 50)
        
        self.stdout.write('\nДанные для входа:')
        self.stdout.write('  Модератор: test_moderator / test123')
        self.stdout.write('  Сотрудник: test_employee / test123')
        
        self.stdout.write('\nСценарии для тестирования:')
        self.stdout.write('  1. Импорт клиента с изменением имени по коду 1С')
        self.stdout.write('  2. Импорт клиента с добавлением кода 1С по имени')
        self.stdout.write('  3. Проверка сохранения задач при обновлении клиента')
        self.stdout.write('  4. Проверка обнаружения дублей')
        self.stdout.write('  5. Проверка пропуска клиентов без совпадений')
