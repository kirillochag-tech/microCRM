# -*- coding: utf-8 -*-
"""
Management command to create test Excel file for 1C import testing.

Creates an Excel file with test data for various import scenarios.
"""

import sys
import io
from django.core.management.base import BaseCommand
from openpyxl import Workbook
from django.conf import settings


class Command(BaseCommand):
    help = 'Создание тестового Excel-файла для импорта клиентов из 1С'

    def handle(self, *args, **options):
        # Fix Windows console encoding
        if sys.platform == 'win32':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        self.stdout.write('Создание тестового Excel-файла для импорта...\n')

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Клиенты"

        # Headers - code_1c вторым после id
        headers = [
            'id',
            'code_1c',
            'name',
            'address',
            'trading_point_name',
            'trading_point_address',
            'stand_count',
            'employee_username'
        ]
        ws.append(headers)

        # Test data for different scenarios:
        # Порядок столбцов: id, code_1c, name, address, trading_point_name, trading_point_address, stand_count, employee_username

        # Scenario 1: Client with 1C code - name will be updated
        # Existing: ООО "Старое Название" (code: 1C-001)
        # New name: ООО "Новое Название" (same code: 1C-001)
        ws.append([
            '',                         # id (пусто для обновления по code_1c)
            '1C-001',                 # code_1c (matches existing)
            'ООО "Новое Название"',  # name (changed)
            'ул. Тестовая, д. 1',     # address
            'Торговая точка 1',       # trading_point_name
            '',                        # trading_point_address
            7,                        # stand_count (changed from 5 to 7)
            'test_employee'           # employee_username
        ])
        self.stdout.write('[OK] Добавлен клиент для сценария 1: Обновление по коду 1С')

        # Scenario 2: Client without 1C code - code will be added
        # Existing: ООО "Вектор" (no code)
        # Will add: code 1C-004
        ws.append([
            '',                         # id (пусто для обновления по name)
            '',                         # code_1c (new code for existing client)
            'ООО "Вектор"',           # name (matches existing)
            'ул. Примерная, д. 10',   # address
            'Вектор-Маркет',          # trading_point_name
            '',                        # trading_point_address
            3,                        # stand_count
            'test_employee'           # employee_username
        ])
        self.stdout.write('[OK] Добавлен клиент для сценария 2: Добавление кода 1С по имени')

        # Scenario 3: Client with 1C code and tasks - verify tasks are preserved
        # Existing: ИП Петров (code: 1C-002) with 2 tasks
        # Update: name and stand_count
        ws.append([
            '',                         # id (пусто для обновления по code_1c)
            '1C-002',                 # code_1c (matches existing with tasks)
            'ИП Петров (обновлено)',  # name (changed)
            'пр. Ленина, д. 50',      # address
            '',                        # trading_point_name
            '',                        # trading_point_address
            4,                        # stand_count (changed from 2 to 4)
            'test_employee'           # employee_username
        ])
        self.stdout.write('[OK] Добавлен клиент для сценария 3: Клиент с задачами (задачи сохранятся)')

        # Scenario 4: Duplicate test - same name as existing
        # Existing: ООО "Альфа" (code: 1C-003)
        # Import: Same name, same code (should update, not create duplicate)
        ws.append([
            '',                         # id (пусто)
            '1C-003',                 # code_1c (matches existing)
            'ООО "Альфа"',            # name (matches existing)
            'ул. Мира, д. 25',        # address
            '',                        # trading_point_name
            '',                        # trading_point_address
            4,                        # stand_count
            'test_employee'           # employee_username
        ])
        self.stdout.write('[OK] Добавлен клиент для сценария 4: Проверка от дублей')

        # Scenario 5: New client - should be skipped (no match by code or name)
        ws.append([
            '',                         # id (пусто)
            '',                         # code_1c (empty, no match)
            'ООО "Гамма"',            # name (new, no match)
            'ул. Новая, д. 100',      # address
            'Гамма-Маркет',           # trading_point_name
            '',                        # trading_point_address
            2,                        # stand_count
            'test_employee'           # employee_username
        ])
        self.stdout.write('[OK] Добавлен клиент для сценария 5: Пропуск (нет совпадений)')

        # Scenario 6: Client with code that doesn't exist - should be skipped
        ws.append([
            '',                         # id (пусто)
            '1C-999',                 # code_1c (doesn't exist)
            'ООО "Дельта"',           # name (new, no match)
            'ул. Промышленная, д. 5', # address
            '',                        # trading_point_name
            '',                        # trading_point_address
            1,                        # stand_count
            'test_employee'           # employee_username
        ])
        self.stdout.write('[OK] Добавлен клиент для сценария 6: Пропуск (код 1С не найден)')

        # Save workbook
        output_path = settings.BASE_DIR / 'test_import_clients.xlsx'
        wb.save(output_path)

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'[OK] Excel-файл создан: {output_path}'))
        self.stdout.write('=' * 50)
        
        self.stdout.write('\nСценарии в файле:')
        self.stdout.write('  Строка 2: Обновление клиента по коду 1С (имя изменится)')
        self.stdout.write('  Строка 3: Добавление кода 1С существующему клиенту')
        self.stdout.write('  Строка 4: Клиент с задачами (задачи сохранятся)')
        self.stdout.write('  Строка 5: Существующий клиент (обновление)')
        self.stdout.write('  Строка 6: Новый клиент без кода (будет пропущен)')
        self.stdout.write('  Строка 7: Клиент с несуществующим кодом (будет пропущен)')
        
        self.stdout.write('\nКак использовать:')
        self.stdout.write('  1. Зайдите в админку как модератор')
        self.stdout.write('  2. Перейдите в раздел "Клиенты"')
        self.stdout.write('  3. Нажмите "Импорт из 1С (Excel)"')
        self.stdout.write('  4. Выберите файл test_import_clients.xlsx')
        self.stdout.write('  5. Проверьте предварительный просмотр')
        self.stdout.write('  6. Подтвердите импорт')
