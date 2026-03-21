@echo off
echo ========================================
echo   Mayrichbe Manager - Windows Web Mode
echo ========================================
echo.

cd /d "%~dp0"
cd backend

if not exist "app\main.py" (
    echo [ERROR] backend folder not found.
    echo Please make sure you extracted all files from the ZIP.
    echo.
    pause
    exit /b 1
)

echo Checking Python...
python --version 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Done.
    echo.
)

echo [2/4] Installing dependencies (first time may be slow)...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel --quiet 2>nul
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet --timeout 180
if errorlevel 1 (
    echo [ERROR] Dependency install failed. Retrying...
    .venv\Scripts\python.exe -m pip install -r requirements.txt --timeout 240
    if errorlevel 1 (
        echo [ERROR] Still failed. Check your internet connection.
        pause
        exit /b 1
    )
)
echo Done.
echo.

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [INFO] Created .env from template.
    )
)

echo [3/4] Initializing database...
.venv\Scripts\python.exe -c "from app.db.init_db import init_db; init_db(); print('Done.')"
if errorlevel 1 (
    echo [ERROR] Database init failed.
    pause
    exit /b 1
)
echo.

echo [4/4] Starting server...
echo.
echo ========================================
echo   URL: http://127.0.0.1:8000
echo   Keep this window open.
echo   Press Ctrl+C to stop.
echo ========================================
echo.

start http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause
