@echo off
setlocal EnableExtensions

rem 防闪退：双击时重新在 cmd /k 窗口中运行并保留输出
if /I not "%~1"=="__RUN_IN_CMD" (
  start "" cmd /k "\"%~f0\" __RUN_IN_CMD"
  exit /b 0
)
shift

chcp 65001 >nul
title Mayrichbe Manager - Windows Diagnostics

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"

echo.
echo ========================================
echo   Mayrichbe Manager - Diagnostics
echo ========================================
echo.

if not exist "%BACKEND%\app\main.py" (
  echo [FAIL] backend folder missing.
  goto :END
) else (
  echo [ OK ] backend folder found.
)

if not exist "%BACKEND%\static\index.html" (
  echo [FAIL] missing frontend static file:
  echo        backend\static\index.html
) else (
  echo [ OK ] frontend static file found.
)

py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
  echo [ OK ] Python 3.11+ available via py -3.11
  goto :AFTER_PY
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
  echo [ OK ] Python 3.11+ available via py -3
  goto :AFTER_PY
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
  echo [ OK ] Python 3.11+ available via python
  goto :AFTER_PY
)

echo [FAIL] Python 3.11+ not found.

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

powershell -NoProfile -Command ^
  "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://local.adspower.net:50325' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo [WARN] AdsPower local API not reachable. Ignore if not using Instagram browser mode.
) else (
  echo [ OK ] AdsPower local API reachable.
)

powershell -NoProfile -Command ^
  "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:54345' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo [WARN] BitBrowser local API not reachable. Ignore if not using BitBrowser.
) else (
  echo [ OK ] BitBrowser local API reachable.
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  echo [WARN] Port 8000 already in use (PID: %%p).
  goto :END
)
echo [ OK ] Port 8000 available.

:END
echo.
echo Diagnostics finished.
echo Fix FAIL items first, then run START_WINDOWS.bat.
echo.
echo Type exit to close this window.
