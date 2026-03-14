@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem 防闪退：双击时重新在 cmd /k 窗口中运行并保留输出
if /I not "%~1"=="__RUN_IN_CMD" (
  start "" cmd /k "\"%~f0\" __RUN_IN_CMD"
  exit /b 0
)
shift

chcp 65001 >nul
title Mayrichbe Manager - Windows Web Launcher

echo.
echo ========================================
echo   Mayrichbe Manager - Windows Web Mode
echo ========================================
echo.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
if not exist "%BACKEND%\app\main.py" (
  echo [ERROR] backend folder not found.
  echo Please run this file from project root.
  goto :END_FAIL
)

if not exist "%BACKEND%\static\index.html" (
  echo [ERROR] frontend static file missing:
  echo         backend\static\index.html
  goto :END_FAIL
)

call :DETECT_PYTHON
if errorlevel 1 goto :END_FAIL

echo [ENV] Python launcher: %PY_CMD%
echo.

cd /d "%BACKEND%"

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    goto :END_FAIL
  )
)

set "VENV_PY=%BACKEND%\.venv\Scripts\python.exe"

echo [2/5] Installing Python dependencies...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel >nul 2>&1
"%VENV_PY%" -m pip install -r requirements.txt --timeout 120
if errorlevel 1 (
  echo [ERROR] Dependency install failed.
  echo Run CHECK_WINDOWS_WEB.bat for diagnostics.
  goto :END_FAIL
)

if not exist ".playwright_chromium_ready" (
  echo [3/5] Installing Playwright Chromium (first run only)...
  "%VENV_PY%" -m playwright install chromium
  if errorlevel 1 (
    echo [ERROR] Playwright browser install failed.
    goto :END_FAIL
  )
  type nul > ".playwright_chromium_ready"
)

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo [INFO] Created backend\.env from template.
  )
)

echo [4/5] Initializing database...
"%VENV_PY%" -c "from app.db.init_db import init_db; init_db(); print('ok')"
if errorlevel 1 (
  echo [ERROR] Database initialization failed.
  goto :END_FAIL
)

echo [5/5] Starting web server...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  echo [WARN] Port 8000 is already in use (PID: %%p).
  echo If app does not open, free the port and retry.
  goto :OPEN_BROWSER
)

:OPEN_BROWSER
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"
echo.
echo URL: http://127.0.0.1:8000
echo Close this window to stop the app.
echo.
"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
goto :EOF

:DETECT_PYTHON
set "PY_CMD="

py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
  set "PY_CMD=py -3.11"
  goto :EOF
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
  set "PY_CMD=py -3"
  goto :EOF
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
  set "PY_CMD=python"
  goto :EOF
)

echo [ERROR] Python 3.11+ not found.
echo Install Python 3.11 or 3.12 and enable "Add Python to PATH".
exit /b 1

:END_FAIL
echo.
echo Startup failed.
echo Run CHECK_WINDOWS_WEB.bat for diagnostics.
echo.
pause
exit /b 1
