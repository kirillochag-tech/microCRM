@echo off
chcp 65001 > nul
call "E:\Разное\Софт\my_venv\web\web\Scripts\activate.bat"
cd /d "%~dp0"
python manage.py runserver
cmd /k