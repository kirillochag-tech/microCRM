"""
Management command to synchronize daily task results from Google Sheets.
"""
from django.core.management.base import BaseCommand
from tasks.services import sync_daily_task_results_from_google_sheet


class Command(BaseCommand):
    help = 'Synchronize daily task results from Google Sheets'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('Starting synchronization from Google Sheets...')
        )
        
        success = sync_daily_task_results_from_google_sheet()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('Successfully synchronized task results from Google Sheets')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Failed to synchronize task results from Google Sheets')
            )