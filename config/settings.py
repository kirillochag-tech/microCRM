# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 20:31:10 2025

@author: Professional
"""

"""
Django settings for employee_management project.

This module contains all configuration settings for the application.
Follows SOLID principles by separating concerns and providing clear configuration.
"""

import os
from pathlib import Path
from datetime import timedelta
import configparser

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# Load configuration from app_config.ini
CONFIG_FILE = Path(__file__).parent / 'app_config.ini'

if CONFIG_FILE.exists():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    SECRET_KEY = config.get('security', 'SECRET_KEY', fallback='django-insecure-fallback-key-for-dev')
else:
    # Fallback for development without config file
    SECRET_KEY = 'django-insecure-fallback-key-for-dev'

# SECURITY WARNING: keep the secret key used in production secret!
# Do not use default value in production

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']  # Configure properly for production

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'import_export',
    'users.apps.UsersConfig',  # Our main app for users
    'tasks.apps.TasksConfig',  # Our main app for tasks
    'clients.apps.ClientsConfig',  # App for client management
    'reports.apps.ReportsConfig',  # App for reports and statistics
    'nested_admin',
    'announcements.apps.AnnouncementsConfig',  # App for announcements system
    'notifications.apps.NotificationsConfig',  # App for notifications
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 4,  # As requested, but note: this is insecure
        }
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'  # Russian interface as requested

USE_I18N = True

USE_TZ = True

# Media files (uploads)
MEDIA_URL = '/media/'

# Load MEDIA_ROOT from config file if available
if CONFIG_FILE.exists():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding=' utf-8')
    media_root_path = config.get('media', 'MEDIA_ROOT', fallback=BASE_DIR / 'media')
    MEDIA_ROOT = Path(media_root_path)
else:
    MEDIA_ROOT = BASE_DIR / 'media'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "tasks" / "static",
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React default
    "http://127.0.0.1:3000",
    "http://localhost:8000",  # Django dev server
    "http://127.0.0.1:8000",  # Django dev server
]

CORS_ALLOW_ALL_ORIGINS = True  # Only for development

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Customize Django admin title
ADMIN_SITE_HEADER = 'Система управления сотрудниками microCRM'
ADMIN_SITE_TITLE = 'Система управления сотрудниками microCRM'
ADMIN_INDEX_TITLE = 'Система управления сотрудниками microCRM'

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Security warning for short passwords
print("WARNING: Password length is set to 4 characters. This is highly insecure for production environments.")

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'  # Russian interface as requested

TIME_ZONE = 'Asia/Krasnoyarsk'  # Красноярское время (UTC+7)

USE_I18N = True

USE_TZ = True

# Добавьте эти строки для поддержки локализации
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

LANGUAGES = [
    ('ru', 'Russian'),
]

# Настройки локализации
USE_I18N = True
USE_L10N = True

# Регистронезависимый поиск для кириллицы в SQLite
import re
import django.db.backends.signals
import django.db.backends.sqlite3

def sqlite_regexp_function(expr, item):
    """Кастомная функция REGEXP для SQLite с поддержкой игнорирования регистра."""
    if item is None:
        return False
    try:
        # Используем re.IGNORECASE для нечувствительности к регистру
        return re.search(expr, item, re.IGNORECASE) is not None
    except re.error:
        return False

def enable_sqlite_regexp(connection, **kwargs):
    """Включает функцию REGEXP в SQLite при создании соединения."""
    if connection.vendor == 'sqlite':
        connection.connection.create_function("REGEXP", 2, sqlite_regexp_function)

# Подключаем сигнал
django.db.backends.signals.connection_created.connect(enable_sqlite_regexp)

# Google Sheets Configuration
GOOGLE_SHEETS_CREDENTIALS = {
    # This is a placeholder - in production, use a proper credentials file
    # The actual credentials should be loaded from environment variables or a secure config
    "type": os.getenv("GOOGLE_SHEETS_TYPE", "service_account"),
    "project_id": os.getenv("GOOGLE_SHEETS_PROJECT_ID", ""),
    "private_key_id": os.getenv("GOOGLE_SHEETS_PRIVATE_KEY_ID", ""),
    "private_key": os.getenv("GOOGLE_SHEETS_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.getenv("GOOGLE_SHEETS_CLIENT_EMAIL", ""),
    "client_id": os.getenv("GOOGLE_SHEETS_CLIENT_ID", ""),
    "auth_uri": os.getenv("GOOGLE_SHEETS_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
    "token_uri": os.getenv("GOOGLE_SHEETS_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_SHEETS_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
    "client_x509_cert_url": os.getenv("GOOGLE_SHEETS_CLIENT_X509_CERT_URL", ""),
}

GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")