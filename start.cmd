@echo off
chcp 65001 > nul
call "%~dp0.venv\Scripts\activate.bat"
cd /d "%~dp0"
python manage.py runserver 0.0.0.0:8000
cmd /k
