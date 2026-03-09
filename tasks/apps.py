from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'
    verbose_name = 'Задачи'

    def ready(self):
        """
        Initialize periodic synchronization when the app is ready.
        """
        try:
            # Only run in the main process (avoid duplicate threads in development server)
            import sys
            if 'runserver' in sys.argv or 'collectstatic' in sys.argv or 'migrate' in sys.argv:
                # Check if this is the main process in development
                import os
                if os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv:
                    from .services import schedule_periodic_sync
                    schedule_periodic_sync()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error initializing periodic sync: {e}")