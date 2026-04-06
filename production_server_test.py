import sys
import os

# Добавляем корневую папку проекта в PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Устанавливаем переменную окружения перед импортом Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Импортируем и настраиваем Django
import django
django.setup()

from waitress import serve

# Импортируем WSGI-приложение из config/
from config.wsgi import application

if __name__ == "__main__":
    print("Starting Waitress server on http://0.0.0.0:8000")
    serve(application, host="0.0.0.0", port=8000, threads=10)
