import sys
import os
import subprocess

# Добавляем корневую папку проекта в PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Путь к виртуальному окружению (как в start.cmd)
venv_path = r"E:\Разное\Софт\my_venv\web\web\Scripts\python.exe"

# Проверяем наличие venv
if os.path.exists(venv_path):
    # Запускаем через venv
    os.execv(venv_path, [venv_path] + sys.argv)
else:
    # Если venv не найден, запускаем как есть
    print("WARNING: Виртуальное окружение не найдено по пути:")
    print(f"  {venv_path}")
    print("Запуск с текущим интерпретатором...")

# Устанавливаем переменную окружения перед импортом Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Импортируем и настраиваем Django
import django
django.setup()

from waitress import serve

# Импортируем WSGI-приложение из config/
from config.wsgi import application

if __name__ == "__main__":
    print("=" * 60)
    print("  ТЕСТОВЫЙ СЕРВЕР MICROCRM")
    print("=" * 60)
    print("  URL: http://0.0.0.0:8001/admin/")
    print("  Порт: 8001")
    print("=" * 60)
    serve(application, host="0.0.0.0", port=8001, threads=10)
