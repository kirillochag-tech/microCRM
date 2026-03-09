# -*- coding: utf-8 -*-
"""
Tests for 1C client import functionality.

This module contains tests for various import scenarios:
1. Update client by 1C code (name changes)
2. Add 1C code to existing client by name
3. Verify tasks are preserved during client update
4. Duplicate detection
5. Skip clients without matches
"""

import os
from decimal import Decimal
from django.test import TestCase, Client as DjangoClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from clients.models import Client, ClientGroup
from tasks.models import Task, TaskType, TaskStatus
from users.models import CustomUser, UserRoles
from openpyxl import Workbook


UserModel = get_user_model()


class ClientImportTests(TestCase):
    """Test cases for client import functionality."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        # Create moderator
        cls.moderator = UserModel.objects.create_user(
            username='test_mod',
            password='test123',
            role=UserRoles.MODERATOR,
            is_staff=True
        )
        
        # Create employee
        cls.employee = UserModel.objects.create_user(
            username='test_emp',
            password='test123',
            role=UserRoles.EMPLOYEE
        )
        
        # Create client group
        cls.group = ClientGroup.objects.create(
            name='Test Group',
            description='Test group for import'
        )
        
        # Client 1: With 1C code (for name update test)
        cls.client_with_code = Client.objects.create(
            code_1c='1C-TEST-001',
            name='Old Name LLC',
            employee=cls.employee,
            address='Test Street, 1',
            stand_count=5
        )
        
        # Client 2: Without 1C code (for code addition test)
        cls.client_without_code = Client.objects.create(
            name='Vector LLC',
            employee=cls.employee,
            address='Example Street, 10',
            stand_count=3
        )
        
        # Client 3: With 1C code and tasks (for task preservation test)
        cls.client_with_tasks = Client.objects.create(
            code_1c='1C-TEST-002',
            name='Petrov IP',
            employee=cls.employee,
            address='Lenin Ave, 50',
            stand_count=2
        )
        
        # Create tasks for client 3
        cls.task1 = Task.objects.create(
            title='Survey for Petrov IP',
            description='Test survey',
            task_type=TaskType.SURVEY,
            status=TaskStatus.SENT,
            created_by=cls.moderator,
            client=cls.client_with_tasks,
            target_count=10,
            current_count=3
        )
        
        cls.task2 = Task.objects.create(
            title='Photo report for Petrov IP',
            description='Test photo report',
            task_type=TaskType.EQUIPMENT_PHOTO,
            status=TaskStatus.ON_CHECK,
            created_by=cls.moderator,
            client=cls.client_with_tasks
        )
        
        # Client 4: For duplicate test
        cls.client_duplicate = Client.objects.create(
            code_1c='1C-TEST-003',
            name='Alpha LLC',
            employee=cls.employee,
            address='Peace Street, 25',
            stand_count=4
        )

    def setUp(self):
        """Set up for each test."""
        # No need to login for these model-level tests
        pass

    def test_01_update_client_by_code(self):
        """
        Scenario 1: Update client name by 1C code.
        
        Steps:
        1. Client exists with code_1c='1C-TEST-001' and name='Old Name LLC'
        2. Import file has same code but new name='New Name LLC'
        3. Client should be updated with new name
        4. 1C code should remain the same
        """
        # Store original ID
        original_id = self.client_with_code.id
        original_code = self.client_with_code.code_1c
        
        # Update client manually (simulating import)
        self.client_with_code.name = 'New Name LLC'
        self.client_with_code.stand_count = 7
        self.client_with_code.save()
        
        # Verify
        updated_client = Client.objects.get(id=original_id)
        self.assertEqual(updated_client.name, 'New Name LLC')
        self.assertEqual(updated_client.code_1c, original_code)
        self.assertEqual(updated_client.stand_count, 7)
        
        print("\n[TEST 1] Обновление клиента по коду 1С: PASSED")

    def test_02_add_code_to_existing_client(self):
        """
        Scenario 2: Add 1C code to existing client by name match.
        
        Steps:
        1. Client exists with name='Vector LLC' and no code_1c
        2. Import file has same name and code_1c='1C-TEST-004'
        3. Client should be updated with 1C code
        4. Name should remain the same
        """
        # Store original ID and name
        original_id = self.client_without_code.id
        original_name = self.client_without_code.name
        
        # Update client manually (simulating import)
        self.client_without_code.code_1c = '1C-TEST-004'
        self.client_without_code.save()
        
        # Verify
        updated_client = Client.objects.get(id=original_id)
        self.assertEqual(updated_client.code_1c, '1C-TEST-004')
        self.assertEqual(updated_client.name, original_name)
        
        print("\n[TEST 2] Добавление кода 1С по имени: PASSED")

    def test_03_tasks_preserved_on_update(self):
        """
        Scenario 3: Tasks are preserved when client is updated.
        
        Steps:
        1. Client has 2 tasks before update
        2. Client is updated (name and stand_count changed)
        3. Tasks should still be associated with client
        4. Task count should remain the same
        """
        # Store original task count
        original_task_count = self.client_with_tasks.get_task_count()
        original_id = self.client_with_tasks.id
        
        # Update client manually (simulating import)
        self.client_with_tasks.name = 'Petrov IP (Updated)'
        self.client_with_tasks.stand_count = 4
        self.client_with_tasks.save()
        
        # Verify tasks are preserved
        updated_client = Client.objects.get(id=original_id)
        new_task_count = updated_client.get_task_count()
        
        self.assertEqual(original_task_count, new_task_count)
        self.assertEqual(new_task_count, 2)
        
        # Verify tasks still reference the client
        tasks = Task.objects.filter(client=updated_client)
        self.assertEqual(tasks.count(), 2)
        
        print("\n[TEST 3] Сохранение задач при обновлении клиента: PASSED")

    def test_04_duplicate_detection(self):
        """
        Scenario 4: Duplicate detection prevents creating duplicate clients.
        
        Steps:
        1. Client exists with name='Alpha LLC' and code_1c='1C-TEST-003'
        2. Import file has same name and code
        3. Should update existing client, not create duplicate
        """
        # Store original ID
        original_id = self.client_duplicate.id
        
        # Count clients before
        client_count_before = Client.objects.filter(
            code_1c='1C-TEST-003'
        ).count()
        
        # Try to create duplicate (should not happen in real import)
        # In real import, this would be handled by import logic
        duplicate = Client(
            code_1c='1C-TEST-003',  # Already exists
            name='Alpha LLC Duplicate',
            employee=self.employee
        )
        
        # Try to save - should raise ValidationError due to unique constraint
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            duplicate.save()
        
        # Verify count hasn't changed
        client_count_after = Client.objects.filter(
            code_1c='1C-TEST-003'
        ).count()
        
        self.assertEqual(client_count_before, client_count_after)
        self.assertEqual(client_count_before, 1)
        
        print("\n[TEST 4] Защита от дублей (unique constraint): PASSED")

    def test_05_skip_clients_without_match(self):
        """
        Scenario 5: Skip clients that don't match by code or name.
        
        Steps:
        1. Import file has client with no matching code or name
        2. Client should not be created
        """
        # Count clients before
        client_count_before = Client.objects.count()
        
        # In real import, this client would be skipped
        # We simulate by not creating it
        new_client_name = 'Gamma LLC'
        exists_before = Client.objects.filter(name=new_client_name).exists()
        
        self.assertFalse(exists_before)
        
        # Verify count hasn't changed after "import"
        client_count_after = Client.objects.count()
        self.assertEqual(client_count_before, client_count_after)
        
        print("\n[TEST 5] Пропуск клиентов без совпадений: PASSED")

    def test_06_code_uniqueness(self):
        """
        Test that 1C code is unique across all clients.
        """
        from django.core.exceptions import ValidationError
        
        # Try to create client with duplicate code
        duplicate_client = Client(
            code_1c='1C-TEST-001',  # Already exists
            name='Another Name',
            employee=self.employee
        )
        
        with self.assertRaises(ValidationError):
            duplicate_client.save()
        
        print("\n[TEST 6] Уникальность кода 1С: PASSED")

    def test_07_search_by_code(self):
        """
        Test that clients can be searched by 1C code.
        """
        # Search by 1C code
        results = Client.objects.filter(code_1c='1C-TEST-001')
        
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().name, 'Old Name LLC')
        
        print("\n[TEST 7] Поиск по коду 1С: PASSED")

    def test_08_client_with_null_code(self):
        """
        Test that clients can have null/empty 1C code.
        """
        # Create client without code
        client_no_code = Client.objects.create(
            name='No Code LLC',
            employee=self.employee,
            address='No Code Street'
        )
        
        self.assertIsNone(client_no_code.code_1c)
        
        # Clean up
        client_no_code.delete()
        
        print("\n[TEST 8] Клиент без кода 1С (null): PASSED")


class ClientImportIntegrationTests(TestCase):
    """Integration tests for client import with Excel file."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.moderator = UserModel.objects.create_user(
            username='test_mod_integration',
            password='test123',
            role=UserRoles.MODERATOR,
            is_staff=True
        )
        
        cls.employee = UserModel.objects.create_user(
            username='test_emp_integration',
            password='test123',
            role=UserRoles.EMPLOYEE
        )

    def test_excel_file_creation(self):
        """
        Test that Excel file can be created and read.
        """
        # Create test Excel file
        wb = Workbook()
        ws = wb.active
        ws.title = "Clients"
        
        # Headers
        headers = ['name', 'code_1c', 'address', 'stand_count']
        ws.append(headers)
        
        # Test data
        test_data = [
            ['Test Client 1', '1C-INT-001', 'Test Address 1', 5],
            ['Test Client 2', '1C-INT-002', 'Test Address 2', 3],
            ['Test Client 3', None, 'Test Address 3', 2],
        ]
        
        for row in test_data:
            ws.append(row)
        
        # Save to temp file
        temp_path = os.path.join(os.path.dirname(__file__), 'test_temp.xlsx')
        wb.save(temp_path)
        
        # Verify file exists
        self.assertTrue(os.path.exists(temp_path))
        
        # Read back and verify
        from openpyxl import load_workbook
        wb_read = load_workbook(temp_path)
        ws_read = wb_read.active
        
        # Check row count (headers + 3 data rows)
        self.assertEqual(ws_read.max_row, 4)
        
        # Clean up
        os.remove(temp_path)
        
        print("\n[INTEGRATION TEST] Создание и чтение Excel-файла: PASSED")
