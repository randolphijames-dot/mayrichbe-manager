@echo off
REM ─────────────────────────────────────────────────────────────────
REM 用 PyInstaller 将 Python 后端打包成 Windows 可执行文件
REM 用法：双击运行，或在命令行执行 electron\scripts\build-backend.bat
REM ─────────────────────────────────────────────────────────────────
set ROOT=%~dp0..\..
set BACKEND=%ROOT%\backend
set DIST_DIR=%ROOT%\electron\backend-dist

echo 🐍 安装 PyInstaller...
cd /d "%BACKEND%"
pip install pyinstaller --quiet

echo 📦 打包 Python 后端...
pyinstaller ^
  --onefile ^
  --name backend_win ^
  --hidden-import "app.api.v1.endpoints.accounts" ^
  --hidden-import "app.api.v1.endpoints.materials" ^
  --hidden-import "app.api.v1.endpoints.tasks" ^
  --hidden-import "app.api.v1.endpoints.logs" ^
  --hidden-import "app.api.v1.endpoints.youtube" ^
  --hidden-import "app.api.v1.endpoints.tools" ^
  --hidden-import "app.api.v1.endpoints.profile" ^
  --hidden-import "app.api.v1.endpoints.inbox" ^
  --hidden-import "app.api.v1.endpoints.traffic" ^
  --hidden-import "apscheduler.triggers.date" ^
  --hidden-import "apscheduler.jobstores.sqlalchemy" ^
  --hidden-import "apscheduler.executors.pool" ^
  --hidden-import "instagrapi" ^
  --collect-all "instagrapi" ^
  --noconfirm ^
  --distpath "%DIST_DIR%" ^
  run_server.py

echo ✅ 后端可执行文件已生成: %DIST_DIR%\backend_win.exe
pause
