@echo off
chcp 65001 >nul 2>&1
title Mayrichbe Manager - 运行中
color 0B
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   Mayrichbe Manager 启动中...        ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0backend"

REM ─── 激活虚拟环境 ───
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo  ⚠ 未找到虚拟环境，请先运行「安装.bat」
    pause
    exit /b 1
)

REM ─── 启动后端 ───
echo  🚀 正在启动后端服务（端口 8000）...
echo.

REM 3 秒后自动打开浏览器
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM 启动 uvicorn（前台运行，关闭此窗口 = 关闭服务）
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo  服务已停止。
pause
