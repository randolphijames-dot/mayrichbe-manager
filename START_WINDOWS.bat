@echo off
chcp 65001 >nul
title Mayrichbe Manager - 启动中...

echo.
echo ========================================
echo   Mayrichbe Manager - 多账号管理系统
echo ========================================
echo.
echo 正在启动后端服务...
echo.

cd /d %~dp0\backend

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖是否安装
if not exist ".venv\" (
    echo [首次运行] 正在创建虚拟环境并安装依赖...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo.
    echo 依赖安装完成！
    echo.
) else (
    call .venv\Scripts\activate.bat
)

:: 启动后端
echo 启动后端服务器...
echo 访问地址: http://localhost:8000
echo.
echo 提示: 关闭此窗口将停止服务
echo.

:: 等待 2 秒后打开浏览器
start /b timeout /t 2 /nobreak >nul && start http://localhost:8000

:: 启动 FastAPI
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
