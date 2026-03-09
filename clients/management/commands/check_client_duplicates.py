# -*- coding: utf-8 -*-
"""
Management command to check for duplicate clients in database.
"""

import sys
import io
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower
from clients.models import Client


class Command(BaseCommand):
    help = 'Проверка базы данных на дубли клиентов'

    def handle(self, *args, **options):
        # Fix Windows console encoding
        if sys.platform == 'win32':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

        print('=' * 60)
        print('ПРОВЕРКА БАЗЫ ДАННЫХ НА ДУБЛИ КЛИЕНТОВ')
        print('=' * 60)

        # 1. Check for duplicates by 1C code
        print('\n1. ДУБЛИ ПО КОДУ 1С:')
        dups_code = list(Client.objects
                         .values('code_1c')
                         .annotate(cnt=Count('id'))
                         .filter(cnt__gt=1)
                         .order_by('-cnt'))
        
        if dups_code:
            print(f'   НАЙДЕНО ДУБЛЕЙ: {len(dups_code)}')
            for d in dups_code:
                if d['code_1c']:
                    clients = Client.objects.filter(code_1c=d['code_1c'])
                    print(f'   Код 1С: {d["code_1c"]}, кол-во: {d["cnt"]}')
                    for c in clients:
                        print(f'      - ID:{c.id} | {c.name}')
        else:
            print('   Дублей не найдено [OK]')

        # 2. Check for duplicates by name
        print('\n2. ДУБЛИ ПО НАИМЕНОВАНИЮ:')
        dups_name = list(Client.objects
                        .values('name')
                        .annotate(cnt=Count('id'))
                        .filter(cnt__gt=1)
                        .order_by('-cnt'))
        
        if dups_name:
            print(f'   НАЙДЕНО ДУБЛЕЙ: {len(dups_name)}')
            for d in dups_name:
                clients = Client.objects.filter(name=d['name'])
                print(f'   Имя: {d["name"]}, кол-во: {d["cnt"]}')
                for c in clients:
                    code_str = f'(код 1С: {c.code_1c})' if c.code_1c else '(без кода 1С)'
                    print(f'      - ID:{c.id} | {code_str}')
        else:
            print('   Дублей не найдено [OK]')

        # 3. General statistics
        print('\n3. ОБЩАЯ СТАТИСТИКА:')
        total_clients = Client.objects.count()
        clients_with_code = Client.objects.exclude(code_1c__isnull=True).exclude(code_1c='').count()
        clients_without_code = Client.objects.filter(code_1c__isnull=True).count()
        clients_empty_code = Client.objects.filter(code_1c='').count()
        
        print(f'   Общее количество клиентов: {total_clients}')
        print(f'   Клиенты с кодом 1С: {clients_with_code}')
        print(f'   Клиенты без кода 1С (NULL): {clients_without_code}')
        print(f'   Клиенты с пустым кодом 1С (""): {clients_empty_code}')

        # 4. List all clients with 1C codes
        print('\n4. ВСЕ КЛИЕНТЫ С КОДОМ 1С:')
        clients_with_codes = Client.objects.exclude(code_1c__isnull=True).exclude(code_1c='').order_by('code_1c')
        for c in clients_with_codes[:50]:  # First 50
            task_count = c.get_task_count() if hasattr(c, 'get_task_count') else 0
            print(f'   ID:{c.id} | Код:{c.code_1c} | {c.name} | Задач:{task_count}')
        
        if len(clients_with_codes) > 50:
            print(f'   ... и ещё {len(clients_with_codes) - 50} клиентов')

        # 5. Check for potential duplicates (similar names)
        print('\n5. ПОТЕНЦИАЛЬНЫЕ ДУБЛИ (похожие имена):')
        print('   (Имена, отличающиеся только регистром)')
        
        case_insensitive_dups = list(Client.objects
                                     .annotate(name_lower=Lower('name'))
                                     .values('name_lower')
                                     .annotate(cnt=Count('id'))
                                     .filter(cnt__gt=1)
                                     .order_by('-cnt'))
        
        if case_insensitive_dups:
            print(f'   Найдено потенциальных дублей: {len(case_insensitive_dups)}')
            for d in case_insensitive_dups[:10]:  # Show first 10
                clients = Client.objects.annotate(name_lower=Lower('name')).filter(name_lower=d['name_lower'])
                names = [c.name for c in clients]
                print(f'   Похожие имена: {names}')
        else:
            print('   Потенциальных дублей не найдено [OK]')

        print('\n' + '=' * 60)
        print('ПРОВЕРКА ЗАВЕРШЕНА')
        print('=' * 60)
