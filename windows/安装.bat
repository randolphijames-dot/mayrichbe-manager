@echo off
chcp 65001 >nul 2>&1
title Mayrichbe Manager - 一键安装
color 0A
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   Mayrichbe Manager 一键安装程序     ║
echo  ║   INS/YT 矩阵管理系统               ║
echo  ╚══════════════════════════════════════╝
echo.

REM ─── 检查 Python ───
echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ⚠ 未检测到 Python！
    echo  请先安装 Python 3.10+：
    echo  https://www.python.org/downloads/
    echo.
    echo  安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
python --version
echo  ✅ Python 已安装
echo.

REM ─── 创建虚拟环境 ───
echo [2/3] 创建虚拟环境并安装依赖（首次约 2-3 分钟）...
cd /d "%~dp0backend"

if not exist "venv" (
    python -m venv venv
    echo  ✅ 虚拟环境已创建
)

call venv\Scripts\activate.bat

pip install -r requirements.txt --quiet 2>&1
if %errorlevel% neq 0 (
    echo  ⚠ 依赖安装失败，尝试用国内镜像...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
)
echo  ✅ Python 依赖安装完成
echo.

REM ─── 创建 .env ───
echo [3/3] 检查配置文件...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo  ✅ 已创建 .env 配置文件
    ) else (
        echo DATABASE_URL=sqlite:///./mayrichbe.db > .env
        echo UPLOAD_DIR=./uploads >> .env
        echo ACCESS_PASSWORD= >> .env
        echo  ✅ 已创建默认 .env 配置文件
    )
) else (
    echo  ✅ .env 已存在，跳过
)

if not exist "uploads" mkdir uploads

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   ✅ 安装完成！                      ║
echo  ║                                      ║
echo  ║   请双击「启动.bat」运行系统          ║
echo  ╚══════════════════════════════════════╝
echo.
pause
