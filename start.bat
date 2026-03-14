@echo off
chcp 65001 > nul
title Social Manager - Windows 启动器
echo.
echo ================================================
echo   Social Manager - Windows 一键启动
echo ================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python。请从 https://python.org 下载安装（选 Add to PATH）
    pause & exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js。请从 https://nodejs.org 下载安装
    pause & exit /b 1
)

:: 检查 Redis（通过 redis-cli）
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [提示] Redis 未运行，尝试启动...
    where redis-server >nul 2>&1
    if errorlevel 1 (
        echo [警告] Redis 未安装。请用 WSL 或下载 https://github.com/microsoftarchive/redis/releases
        echo [警告] 暂时跳过 Redis，定时任务将无法执行
    ) else (
        start "Redis" /min redis-server
        timeout /t 2 /nobreak >nul
    )
)

:: 安装后端依赖
echo [1/4] 检查后端依赖...
cd backend
if not exist ".venv" (
    echo 创建虚拟环境...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q --disable-pip-version-check
if not exist ".env" (
    copy .env.example .env
    echo [提示] 已创建 .env，请按需修改配置
)

:: 初始化数据库
python -c "from app.db.init_db import init_db; init_db()" 2>nul

:: 启动后端
echo [2/4] 启动后端 API...
start "后端API" cmd /k "call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

:: 启动 Celery Worker
echo [3/4] 启动 Celery Worker...
start "Celery Worker" cmd /k "call .venv\Scripts\activate.bat && celery -A app.tasks.celery_app worker -l info -Q default,instagram,youtube --pool=solo"
timeout /t 2 /nobreak >nul

:: 启动 Celery Beat
start "Celery Beat" cmd /k "call .venv\Scripts\activate.bat && celery -A app.tasks.celery_app beat -l info"

:: 安装前端依赖 & 启动
echo [4/4] 启动前端...
cd ..\frontend
if not exist "node_modules" (
    echo 安装前端依赖（首次需要几分钟）...
    npm install
)
start "前端" cmd /k "npm run dev"

cd ..
echo.
echo ================================================
echo   启动完成！
echo   前端：http://localhost:5173
echo   API: http://localhost:8000
echo   文档：http://localhost:8000/docs
echo.
echo   局域网访问（其他电脑）：
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R "IPv4.*192\."') do (
    echo   http://%%a:5173  （局域网 IP）
)
echo ================================================
echo.
pause
