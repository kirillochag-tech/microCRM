@echo off
chcp 65001 > nul
call "%~dp0.venv\Scripts\activate.bat"
cd /d "%~dp0"
echo ============================================================
echo   ТЕСТОВЫЙ СЕРВЕР MICROCRM (Порт 8001)
echo ============================================================
echo.
python production_server_test.py
cmd /k
