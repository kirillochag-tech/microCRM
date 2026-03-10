import sys
import os
from waitress import serve
from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler

# Добавляем корневую папку проекта в PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Импортируем WSGI-приложение из config/
from config.wsgi import application

# Обертка для раздачи статических файлов в production
class StaticFilesServer:
    def __init__(self, app):
        self.app = app
        self.static_handler = StaticFilesHandler(app)
    
    def __call__(self, environ, start_response):
        return self.static_handler(environ, start_response)

if __name__ == "__main__":
    print("Starting Waitress server on http://0.0.0.0:8001")
    serve(StaticFilesServer(application), host="0.0.0.0", port=8001, threads=6)
