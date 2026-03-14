@echo off
setlocal EnableExtensions EnableDelayedExpansion

if /I not "%~1"=="__RUN_IN_CMD" (
  start "" cmd /k "\"%~f0\" __RUN_IN_CMD"
  exit /b 0
)
shift

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "BACKEND=%ROOT%backend"
set "LOG_DIR=%ROOT%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\start_windows.log"

echo ==================================================>>"%LOG_FILE%"
echo [%%date%% %%time%%] START>>"%LOG_FILE%"
echo ROOT=%ROOT%>>"%LOG_FILE%"

echo.
echo ========================================
echo   Mayrichbe Manager - Windows Web Mode
echo ========================================
echo.

if not exist "%BACKEND%\app\main.py" (
  echo [ERROR] backend folder not found.
  echo [ERROR] See log: %LOG_FILE%
  goto :END_FAIL
)

if not exist "%BACKEND%\static\index.html" (
  echo [ERROR] frontend static file missing: backend\static\index.html
  echo [ERROR] See log: %LOG_FILE%
  goto :END_FAIL
)

call :DETECT_PYTHON
if errorlevel 1 goto :END_FAIL

echo [ENV] Python launcher: %PY_CMD%
echo [ENV] Python launcher: %PY_CMD%>>"%LOG_FILE%"

cd /d "%BACKEND%"

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating virtual environment...
  %PY_CMD% -m venv .venv >>"%LOG_FILE%" 2>&1
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    echo [ERROR] See log: %LOG_FILE%
    goto :END_FAIL
  )
)

set "VENV_PY=%BACKEND%\.venv\Scripts\python.exe"

echo [2/5] Installing Python dependencies...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel >>"%LOG_FILE%" 2>&1
"%VENV_PY%" -m pip install -r requirements.txt --timeout 180 --prefer-binary >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo [WARN] First dependency install failed, retrying...
  "%VENV_PY%" -m pip install -r requirements.txt --timeout 240 >>"%LOG_FILE%" 2>&1
)
if errorlevel 1 (
  echo [ERROR] Dependency install failed.
  echo [ERROR] See log: %LOG_FILE%
  echo [HINT] Run CHECK_WINDOWS_WEB.bat for diagnostics.
  goto :END_FAIL
)

if not exist ".playwright_chromium_ready" (
  echo [3/5] Installing Playwright Chromium (optional)...
  "%VENV_PY%" -m playwright install chromium >>"%LOG_FILE%" 2>&1
  if errorlevel 1 (
    echo [WARN] Playwright install failed. Core web app can still start.
    echo [WARN] Playwright install failed.>>"%LOG_FILE%"
  ) else (
    type nul > ".playwright_chromium_ready"
  )
)

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo [INFO] Created backend\.env from template.
    echo [INFO] Created backend\.env from template.>>"%LOG_FILE%"
  )
)

echo [4/5] Initializing database...
"%VENV_PY%" -c "from app.db.init_db import init_db; init_db(); print('ok')" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo [ERROR] Database initialization failed.
  echo [ERROR] See log: %LOG_FILE%
  goto :END_FAIL
)

echo [5/5] Starting web server...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  echo [WARN] Port 8000 is already in use (PID: %%p).
  echo [WARN] Port 8000 already in use, PID=%%p>>"%LOG_FILE%"
  goto :OPEN_BROWSER
)

:OPEN_BROWSER
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"
echo.
echo URL: http://127.0.0.1:8000
echo Log: %LOG_FILE%
echo Keep this window open while app is running.
echo.
"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >>"%LOG_FILE%" 2>&1
echo.
echo [INFO] Server stopped. Log: %LOG_FILE%
goto :EOF

:DETECT_PYTHON
set "PY_CMD="

for %%V in (3.12 3.11 3.10) do (
  py -%%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=py -%%V"
    goto :EOF
  )
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
  set "PY_CMD=python"
  goto :EOF
)

echo [ERROR] Python 3.10+ not found.
echo [ERROR] Python 3.10+ not found.>>"%LOG_FILE%"
exit /b 1

:END_FAIL
echo.
echo Startup failed.
echo Please run CHECK_WINDOWS_WEB.bat and send me this log:
echo   %LOG_FILE%
echo.
