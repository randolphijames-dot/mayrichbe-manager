@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Windows 版本诊断工具

echo ========================================
echo   Mayrichbe Manager - 诊断工具
echo ========================================
echo.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "LOG_FILE=%ROOT%诊断报告_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.txt"

echo 正在收集系统信息...
echo 诊断报告 - %date% %time% > "%LOG_FILE%"
echo ========================================>> "%LOG_FILE%"
echo.>> "%LOG_FILE%"

echo [1/8] 检查 Python 环境...
echo === Python 环境 ===>> "%LOG_FILE%"
python --version >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到 PATH
    echo [ERROR] Python not found>> "%LOG_FILE%"
) else (
    echo ✅ Python 已安装
)
echo.>> "%LOG_FILE%"

echo [2/8] 检查文件完整性...
echo === 文件检查 ===>> "%LOG_FILE%"
if exist "%BACKEND%\app\main.py" (
    echo ✅ 后端文件存在
    echo [OK] backend files>> "%LOG_FILE%"
) else (
    echo ❌ 后端文件缺失
    echo [ERROR] backend files missing>> "%LOG_FILE%"
)

if exist "%BACKEND%\static\index.html" (
    echo ✅ 前端文件存在
    echo [OK] frontend files>> "%LOG_FILE%"
) else (
    echo ❌ 前端文件缺失
    echo [ERROR] frontend files missing>> "%LOG_FILE%"
)
echo.>> "%LOG_FILE%"

echo [3/8] 检查端口占用...
echo === 端口检查 ===>> "%LOG_FILE%"
netstat -ano | findstr ":8000" >> "%LOG_FILE%"
if errorlevel 1 (
    echo ⚠️  端口 8000 未被占用（服务可能未启动）
) else (
    echo ✅ 端口 8000 已被占用（服务可能在运行）
)
echo.>> "%LOG_FILE%"

echo [4/8] 检查虚拟环境...
echo === 虚拟环境 ===>> "%LOG_FILE%"
if exist "%BACKEND%\.venv\Scripts\python.exe" (
    echo ✅ 虚拟环境已创建
    echo [OK] venv exists>> "%LOG_FILE%"
) else (
    echo ⚠️  虚拟环境不存在（首次运行会自动创建）
    echo [WARN] venv not found>> "%LOG_FILE%"
)
echo.>> "%LOG_FILE%"

echo [5/8] 检查数据库...
echo === 数据库检查 ===>> "%LOG_FILE%"
if exist "%BACKEND%\social_manager.db" (
    echo ✅ 数据库文件存在
    echo [OK] database exists>> "%LOG_FILE%"
    dir "%BACKEND%\social_manager.db" >> "%LOG_FILE%"

    REM 查询素材数量
    if exist "%BACKEND%\.venv\Scripts\python.exe" (
        echo 正在查询数据...
        "%BACKEND%\.venv\Scripts\python.exe" -c "import sqlite3; conn=sqlite3.connect(r'%BACKEND%\social_manager.db'); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM materials'); print(f'素材数量: {cur.fetchone()[0]}'); cur.execute('SELECT COUNT(*) FROM accounts'); print(f'账号数量: {cur.fetchone()[0]}'); cur.execute('SELECT COUNT(*) FROM tasks'); print(f'任务数量: {cur.fetchone()[0]}'); conn.close()" >> "%LOG_FILE%" 2>&1
    )
) else (
    echo ⚠️  数据库不存在（首次运行会自动创建）
    echo [WARN] database not found>> "%LOG_FILE%"
)
echo.>> "%LOG_FILE%"

echo [6/8] 检查 BitBrowser / AdsPower...
echo === 指纹浏览器检查 ===>> "%LOG_FILE%"
curl -s http://127.0.0.1:54345/api/v1/browser/list >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ⚠️  BitBrowser 未运行或未安装
    echo [WARN] BitBrowser not accessible>> "%LOG_FILE%"
) else (
    echo ✅ BitBrowser 可访问
    echo [OK] BitBrowser running>> "%LOG_FILE%"
)

curl -s http://127.0.0.1:50325/api/v1/browser/list >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ⚠️  AdsPower 未运行或未安装
    echo [WARN] AdsPower not accessible>> "%LOG_FILE%"
) else (
    echo ✅ AdsPower 可访问
    echo [OK] AdsPower running>> "%LOG_FILE%"
)
echo.>> "%LOG_FILE%"

echo [7/8] 尝试连接后端 API...
echo === 后端 API 测试 ===>> "%LOG_FILE%"
curl -s http://127.0.0.1:8000/ >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ❌ 后端服务未响应
    echo [ERROR] backend not responding>> "%LOG_FILE%"
    echo.
    echo 💡 请先双击 START_WINDOWS.bat 启动服务
) else (
    echo ✅ 后端服务正常
    echo [OK] backend responding>> "%LOG_FILE%"

    echo.
    echo 正在获取任务列表（最近5个）...
    curl -s "http://127.0.0.1:8000/api/v1/tasks/?limit=5" >> "%LOG_FILE%"
)
echo.>> "%LOG_FILE%"

echo [8/8] 检查最近的发布任务状态...
if exist "%BACKEND%\.venv\Scripts\python.exe" (
    if exist "%BACKEND%\social_manager.db" (
        echo === 最近任务状态 ===>> "%LOG_FILE%"
        "%BACKEND%\.venv\Scripts\python.exe" -c "import sqlite3; conn=sqlite3.connect(r'%BACKEND%\social_manager.db'); cur=conn.cursor(); cur.execute('SELECT id, platform, status, scheduled_at, error_message FROM tasks ORDER BY id DESC LIMIT 5'); print('\n最近5个任务:'); [print(f'任务 #{row[0]}: {row[1]} - {row[2]} (计划时间: {row[3]})' + (f'\n  错误: {row[4]}' if row[4] else '')) for row in cur.fetchall()]; conn.close()" >> "%LOG_FILE%" 2>&1
    )
)
echo.>> "%LOG_FILE%"

echo.
echo ========================================
echo 诊断完成！
echo.
echo 报告已保存到:
echo %LOG_FILE%
echo.
echo 请将此文件发送给技术支持。
echo ========================================
echo.
pause
