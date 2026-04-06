@echo off
chcp 65001 > nul

cd /d "%~dp0"
python manage.py runserver 0.0.0.0:8000
cmd /k