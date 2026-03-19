@echo off
setlocal EnableExtensions

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
set "LOG_FILE=%LOG_DIR%\check_windows.log"

echo ==================================================>>"%LOG_FILE%"
echo [%%date%% %%time%%] CHECK>>"%LOG_FILE%"

echo.
echo ========================================
echo   Mayrichbe Manager - Diagnostics
echo ========================================
echo.

if not exist "%BACKEND%\app\main.py" (
  echo [FAIL] backend folder missing.
  echo [FAIL] backend folder missing.>>"%LOG_FILE%"
  goto :END
) else (
  echo [ OK ] backend folder found.
)

if not exist "%BACKEND%\static\index.html" (
  echo [FAIL] missing frontend static file: backend\static\index.html
  echo [FAIL] missing frontend static file.>>"%LOG_FILE%"
) else (
  echo [ OK ] frontend static file found.
)

set "PY_OK="
for %%V in (3.12 3.11 3.10) do (
  py -%%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    echo [ OK ] Python 3.10+ available via py -%%V
    echo [ OK ] Python via py -%%V>>"%LOG_FILE%"
    set "PY_OK=1"
    goto :AFTER_PY
  )
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 (
  echo [ OK ] Python 3.10+ available via python
  echo [ OK ] Python via python>>"%LOG_FILE%"
  set "PY_OK=1"
  goto :AFTER_PY
)

echo [FAIL] Python 3.10+ not found.
echo [FAIL] Python 3.10+ not found.>>"%LOG_FILE%"

:AFTER_PY
if exist "%BACKEND%\.env" (
  echo [ OK ] backend\.env exists.
) else (
  echo [WARN] backend\.env missing (first start will create it).
)

if exist "%BACKEND%\.venv\Scripts\python.exe" (
  echo [ OK ] virtual environment exists.
) else (
  echo [WARN] virtual environment missing (first start will create it).
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  echo [WARN] Port 8000 already in use (PID: %%p).
  echo [WARN] Port 8000 in use PID=%%p>>"%LOG_FILE%"
  goto :END
)
echo [ OK ] Port 8000 available.

:END
echo.
echo Diagnostics finished.
echo Log file: %LOG_FILE%
echo.
echo Please send me this file if it still fails.
