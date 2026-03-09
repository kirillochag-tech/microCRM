# -*- coding: utf-8 -*-
"""
Management command to import clients from Excel file with 1C code update.
"""

import sys
import io
from django.core.management.base import BaseCommand
from openpyxl import load_workbook
from clients.models import Client


class Command(BaseCommand):
    help = 'Импорт клиентов из Excel файла с обновлением code_1c'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='Клиенты выгрузка.xlsx', help='Путь к Excel файлу')
        parser.add_argument('--test', action='store_true', help='Тестовый режим (без сохранения)')

    def handle(self, *args, **options):
        # Fix Windows console encoding
        if sys.platform == 'win32':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

        file_path = options.get('file', 'Клиенты выгрузка.xlsx')
        test_mode = options.get('test', False)

        self.stdout.write(f'=== ИМПОРТ КЛИЕНТОВ ИЗ {file_path} ===')
        if test_mode:
            self.stdout.write('!!! ТЕСТОВЫЙ РЕЖИМ (без сохранения) !!!\n')

        # Load the file
        wb = load_workbook(file_path)
        ws = wb.active

        # Get headers
        headers = [cell.value for cell in ws[1]]
        self.stdout.write(f'Заголовки: {headers}\n')

        # Statistics
        updated = 0
        not_found = 0
        total = 0

        # Process rows
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            code_1c = str(row[1]) if row[1] and str(row[1]).strip() else None
            name = row[2] if len(row) > 2 and row[2] else None

            if not name:
                continue

            total += 1
            instance = None
            found_by = None

            # Step 1: Try to find by code_1c
            if code_1c:
                instance = Client.objects.filter(code_1c=code_1c).first()
                if instance:
                    found_by = 'code_1c'

            # Step 2: If not found, try to find by name
            if not instance and name:
                instance = Client.objects.filter(name=name).first()
                if instance:
                    found_by = 'name'

            # Step 3: Update if found
            if instance:
                old_code = instance.code_1c
                if code_1c:
                    instance.code_1c = code_1c
                if not test_mode:
                    instance.save()
                
                status = 'обновлен' if old_code != code_1c else 'без изменений'
                if total <= 10 or not_found < 5:  # Show first 10 and first 5 not found
                    self.stdout.write(f"  [{row_idx}] {found_by}: ID={instance.id} | {name[:50]}... | code_1c: {old_code} -> {code_1c} [{status}]")
                updated += 1
            else:
                if not_found < 10:  # Show first 10 not found
                    self.stdout.write(f'  [{row_idx}] НЕ НАЙДЕН: {name[:50]}... (code_1c={code_1c})')
                not_found += 1

            if total == 10:
                self.stdout.write('  ... (пропуск вывода) ...\n')

        self.stdout.write(f'\n=== ИТОГИ ===')
        self.stdout.write(f'Всего строк: {total}')
        self.stdout.write(f'Обновлено: {updated}')
        self.stdout.write(f'Не найдено: {not_found}')
        
        if test_mode:
            self.stdout.write('\n!!! ТЕСТОВЫЙ РЕЖИМ - изменения не сохранены !!!')
            self.stdout.write('Для реального импорта запустите без --test')
