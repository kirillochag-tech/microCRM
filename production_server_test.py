import sys
import os

# Добавляем корневую папку проекта в PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Путь к виртуальному окружению в папке проекта
venv_path = os.path.join(project_root, '.venv', 'Scripts', 'python.exe')

# Проверяем наличие venv и запускаем через него
if os.path.exists(venv_path):
    print(f"Using virtual environment: {venv_path}")
    os.execv(venv_path, [venv_path] + sys.argv)
else:
    print("WARNING: Виртуальное окружение не найдено.")
    print("Запуск с текущим интерпретатором...")
    print()

# Устанавливаем переменную окружения перед импортом Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Импортируем и настраиваем Django
import django
django.setup()

from waitress import serve
from django.contrib.staticfiles.handlers import StaticFilesHandler

# Импортируем WSGI-приложение из config/ и оборачиваем в StaticFilesHandler
from config.wsgi import application
application = StaticFilesHandler(application)

if __name__ == "__main__":
    print("=" * 60)
    print("  ТЕСТОВЫЙ СЕРВЕР MICROCRM")
    print("=" * 60)
    print("  URL: http://0.0.0.0:8001/admin/")
    print("  Порт: 8001")
    print("=" * 60)
    serve(application, host="0.0.0.0", port=8001, threads=10)
