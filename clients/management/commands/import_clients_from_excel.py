# -*- coding: utf-8 -*-
"""
Management command to import clients from Excel file with 1C code update.
"""

from django.core.management.base import BaseCommand
from openpyxl import load_workbook
from clients.models import Client


class Command(BaseCommand):
    help = 'Импорт клиентов из Excel файла с обновлением code_1c'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='Клиенты выгрузка.xlsx', help='Путь к Excel файлу')
        parser.add_argument('--test', action='store_true', help='Тестовый режим (без сохранения)')

    def handle(self, *args, **options):
        file_path = options.get('file', 'Клиенты выгрузка.xlsx')
        test_mode = options.get('test', False)

        # Load the file
        wb = load_workbook(file_path)
        ws = wb.active

        # Statistics
        updated = 0
        not_found = 0
        total = 0
        updated_list = []
        not_found_list = []

        # Process rows
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            code_1c = str(row[1]) if row[1] and str(row[1]).strip() else None
            name = row[2] if len(row) > 2 and row[2] else None

            if not name:
                continue

            total += 1
            instance = None

            # Step 1: Try to find by code_1c
            if code_1c:
                instance = Client.objects.filter(code_1c=code_1c).first()

            # Step 2: If not found, try to find by name
            if not instance and name:
                instance = Client.objects.filter(name=name).first()

            # Step 3: Update if found
            if instance:
                old_code = instance.code_1c
                if code_1c:
                    instance.code_1c = code_1c
                if not test_mode:
                    instance.save()
                
                status = 'updated' if old_code != code_1c else 'unchanged'
                updated_list.append({
                    'row': row_idx,
                    'id': instance.id,
                    'name': name[:50],
                    'old_code': old_code,
                    'new_code': code_1c,
                    'status': status
                })
                updated += 1
            else:
                not_found_list.append({
                    'row': row_idx,
                    'name': name[:50],
                    'code_1c': code_1c
                })
                not_found += 1

        # Print results - simple format for Windows compatibility
        print('=' * 70)
        print('         IMPORT CLIENTS FROM 1C (Excel)')
        print('=' * 70)
        print(f'File: {file_path}')
        if test_mode:
            print('*** TEST MODE - NO CHANGES SAVED ***')
        print()
        print('SUMMARY:')
        print(f'  Total rows processed: {total}')
        print(f'  Clients updated:      {updated}')
        print(f'  Not found in DB:      {not_found}')
        print()

        if updated > 0:
            print('UPDATED CLIENTS (first 20):')
            print(f'{"Row":<6} {"ID":<6} {"Name":<50} {"code_1c":<12}')
            print('-' * 70)
            for item in updated_list[:20]:
                icon = '+' if item['status'] == 'updated' else ' '
                print(f"{icon} {item['row']:<5} {item['id']:<6} {item['name']:<50} {item['new_code']:<12}")
            if len(updated_list) > 20:
                print(f'  ... and {len(updated_list) - 20} more clients')
            print()

        if not_found > 0:
            print('NOT FOUND (need to create in DB):')
            print(f'{"Row":<6} {"code_1c":<12} {"Name":<50}')
            print('-' * 70)
            for item in not_found_list[:20]:
                code = item['code_1c'] if item['code_1c'] else 'N/A'
                print(f"  {item['row']:<5} {code:<12} {item['name']:<50}")
            if len(not_found_list) > 20:
                print(f'  ... and {len(not_found_list) - 20} more clients')
            print()

        print('=' * 70)
        if test_mode:
            print('!!! TEST MODE - NO CHANGES SAVED TO DATABASE !!!')
            print('Run without --test to save changes')
        else:
            print('Import completed successfully!')
        print('=' * 70)
