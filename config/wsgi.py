"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Настройка заголовков админ-панели (после инициализации Django)
from django.contrib import admin
from django.conf import settings

admin.site.site_header = getattr(settings, 'ADMIN_SITE_HEADER', 'Administration')
admin.site.site_title = getattr(settings, 'ADMIN_SITE_TITLE', 'Admin Panel')
admin.site.index_title = getattr(settings, 'ADMIN_INDEX_TITLE', 'Welcome to Admin Panel')
