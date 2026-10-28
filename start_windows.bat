@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto failure
)
".venv\Scripts\python.exe" -c "import flask" >nul 2>nul
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto failure
)
".venv\Scripts\python.exe" run.py %*
if errorlevel 1 goto failure
exit /b 0
:failure
echo Не удалось запустить. Установите Python 3.11+ и проверьте подключение к интернету для первой установки.
pause
exit /b 1
