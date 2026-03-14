# Windows Web 版打包技能

## 问题背景

在 Mac 上直接创建的 `.bat` 文件在 Windows 上无法运行，会出现以下问题：
- 闪退或黑屏
- 报错 "is not recognized as an internal or external command"
- 中文乱码

## 根本原因

1. **行尾符问题**：Mac/Linux 使用 LF (`\n`)，Windows 需要 CRLF (`\r\n`)
2. **编码问题**：Mac 默认 UTF-8，Windows cmd 需要 GBK/ANSI
3. **路径空格处理**：复杂的引号嵌套在包含空格的路径下会失败
4. **前端构建输出**：相对路径在不同系统中解析不同

## 解决方案：使用 GitHub Actions 在 Windows 环境中打包

### 优势
- ✅ 在真实 Windows 环境中创建文件，保证兼容性
- ✅ bat 文件自动使用正确的编码和行尾符
- ✅ 可以验证前端构建是否成功
- ✅ 可重复、可追溯

### Workflow 配置文件

文件位置：`.github/workflows/build-windows-web.yml`

```yaml
name: Build Windows Web Package

on:
  workflow_dispatch:

jobs:
  build-web:
    runs-on: windows-latest
    timeout-minutes: 30

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install frontend dependencies
        shell: cmd
        run: |
          cd frontend
          npm ci
          if errorlevel 1 exit /b 1

      - name: Build frontend
        shell: cmd
        run: |
          cd frontend
          npm run build
          if errorlevel 1 exit /b 1

      - name: Verify frontend build output
        shell: cmd
        run: |
          if not exist "backend\static\index.html" (
            echo [ERROR] Frontend build failed - index.html not found
            dir backend
            exit /b 1
          )
          echo [OK] Frontend static files ready
          dir backend\static

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Create Windows Web package
        shell: cmd
        run: |
          mkdir dist-web-windows
          mkdir dist-web-windows\Mayrichbe-Manager-Web

          echo Creating START_WINDOWS.bat...
          (
            echo @echo off
            echo chcp 65001 ^>nul
            echo setlocal EnableExtensions EnableDelayedExpansion
            echo title Mayrichbe Manager - Windows Web Launcher
            echo.
            echo echo ========================================
            echo echo   Mayrichbe Manager - Windows Web Mode
            echo echo ========================================
            echo echo.
            echo.
            echo set "ROOT=%%~dp0"
            echo set "BACKEND=%%ROOT%%backend"
            echo if not exist "%%BACKEND%%\app\main.py" ^(
            echo   echo [ERROR] backend folder not found.
            echo   goto :END_FAIL
            echo ^)
            echo.
            echo if not exist "%%BACKEND%%\static\index.html" ^(
            echo   echo [ERROR] frontend static file missing.
            echo   goto :END_FAIL
            echo ^)
            echo.
            echo call :DETECT_PYTHON
            echo if errorlevel 1 goto :END_FAIL
            echo.
            echo cd /d "%%BACKEND%%"
            echo.
            echo if not exist ".venv\Scripts\python.exe" ^(
            echo   echo [1/5] Creating virtual environment...
            echo   %%PY_CMD%% -m venv .venv
            echo ^)
            echo.
            echo set "VENV_PY=%%BACKEND%%\.venv\Scripts\python.exe"
            echo.
            echo echo [2/5] Installing Python dependencies...
            echo "%%VENV_PY%%" -m pip install --upgrade pip setuptools wheel ^>nul 2^>^&1
            echo "%%VENV_PY%%" -m pip install -r requirements.txt --timeout 120
            echo if errorlevel 1 goto :END_FAIL
            echo.
            echo if not exist ".playwright_chromium_ready" ^(
            echo   echo [3/5] Installing Playwright Chromium...
            echo   "%%VENV_PY%%" -m playwright install chromium
            echo   if errorlevel 1 goto :END_FAIL
            echo   type nul ^> ".playwright_chromium_ready"
            echo ^)
            echo.
            echo if not exist ".env" ^(
            echo   if exist ".env.example" copy ".env.example" ".env" ^>nul
            echo ^)
            echo.
            echo echo [4/5] Initializing database...
            echo "%%VENV_PY%%" -c "from app.db.init_db import init_db; init_db()"
            echo if errorlevel 1 goto :END_FAIL
            echo.
            echo echo [5/5] Starting web server...
            echo start "" http://127.0.0.1:8000
            echo echo.
            echo echo URL: http://127.0.0.1:8000
            echo echo Close this window to stop the app.
            echo echo.
            echo "%%VENV_PY%%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
            echo goto :EOF
            echo.
            echo :DETECT_PYTHON
            echo set "PY_CMD="
            echo py -3.11 --version ^>nul 2^>^&1
            echo if not errorlevel 1 ^(
            echo   set "PY_CMD=py -3.11"
            echo   goto :EOF
            echo ^)
            echo py -3 --version ^>nul 2^>^&1
            echo if not errorlevel 1 ^(
            echo   set "PY_CMD=py -3"
            echo   goto :EOF
            echo ^)
            echo python --version ^>nul 2^>^&1
            echo if not errorlevel 1 ^(
            echo   set "PY_CMD=python"
            echo   goto :EOF
            echo ^)
            echo echo [ERROR] Python 3.11+ not found.
            echo exit /b 1
            echo.
            echo :END_FAIL
            echo echo.
            echo echo Startup failed.
            echo echo.
            echo pause
            echo exit /b 1
          ) > dist-web-windows\Mayrichbe-Manager-Web\START_WINDOWS.bat

          echo Creating README...
          (
            echo # Mayrichbe Manager - Windows Web Version
            echo.
            echo ## Quick Start
            echo.
            echo 1. Install Python 3.11+ ^(check "Add Python to PATH"^)
            echo 2. Double-click START_WINDOWS.bat
            echo 3. Browser will open http://127.0.0.1:8000
            echo.
            echo ## Requirements
            echo.
            echo - Windows 10/11
            echo - Python 3.11 or 3.12
            echo.
            echo ## First Run
            echo.
            echo The script will automatically:
            echo - Create virtual environment
            echo - Install dependencies
            echo - Install Playwright Chromium
            echo - Initialize database
            echo - Start web server
            echo.
          ) > dist-web-windows\Mayrichbe-Manager-Web\README.txt

      - name: Copy backend files
        shell: cmd
        run: |
          xcopy /E /I /Y backend dist-web-windows\Mayrichbe-Manager-Web\backend
          rmdir /S /Q dist-web-windows\Mayrichbe-Manager-Web\backend\.venv 2>nul
          rmdir /S /Q dist-web-windows\Mayrichbe-Manager-Web\backend\__pycache__ 2>nul
          del /Q dist-web-windows\Mayrichbe-Manager-Web\backend\social_manager.db 2>nul
          mkdir dist-web-windows\Mayrichbe-Manager-Web\backend\uploads 2>nul

      - name: Create ZIP
        shell: pwsh
        run: |
          Compress-Archive -Path "dist-web-windows\Mayrichbe-Manager-Web\*" -DestinationPath "dist-web-windows\Mayrichbe-Manager-Web.zip" -Force

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: mayrichbe-manager-windows-web
          path: dist-web-windows/Mayrichbe-Manager-Web.zip
          retention-days: 7
```

## 使用方法

### 1. 触发打包

```bash
# 方法 1：使用 gh CLI
gh workflow run build-windows-web.yml

# 方法 2：GitHub 网页
# 访问 Actions 标签页 → 选择 workflow → Run workflow
```

### 2. 等待构建完成

```bash
# 监控运行状态
gh run watch <RUN_ID>

# 或查看最新运行
gh run list --workflow=build-windows-web.yml --limit 1
```

### 3. 下载产物

```bash
# 下载到本地
gh run download <RUN_ID> -D ./dist-windows-github

# 产物位置
# dist-windows-github/mayrichbe-manager-windows-web/Mayrichbe-Manager-Web.zip
```

### 4. 分发给 Windows 用户

将 zip 文件发送给 Windows 用户，使用说明：
1. 安装 Python 3.11+ （勾选 "Add Python to PATH"）
2. 解压到**无空格路径**（如 `C:\Mayrichbe`）
3. 双击 `START_WINDOWS.bat`
4. 首次运行会自动安装依赖（需要几分钟）
5. 浏览器自动打开 `http://127.0.0.1:8000`

## 关键要点

### ✅ 正确做法
- 在 Windows 环境中创建 bat 文件
- 分步骤验证前端构建（Install → Build → Verify）
- 使用简单的启动逻辑，避免复杂引号嵌套
- 提供清晰的错误提示

### ❌ 常见错误
- 在 Mac 上直接创建 bat 文件
- 没有验证前端构建输出
- 使用包含空格的路径
- 没有检查 Python 是否在 PATH 中

## 故障排查

### 问题 1：bat 文件闪退
**原因**：编码或行尾符问题
**解决**：使用 GitHub Actions 重新打包

### 问题 2：Python 未找到
**原因**：Windows 电脑未安装 Python 或未添加到 PATH
**解决**：安装 Python 3.11+ 并勾选 "Add Python to PATH"

### 问题 3：前端静态文件缺失
**原因**：前端构建失败或输出路径错误
**解决**：检查 workflow 日志中的 "Verify frontend build output" 步骤

### 问题 4：路径包含空格导致失败
**原因**：bat 脚本中的引号处理问题
**解决**：建议用户解压到无空格路径（如 `C:\Mayrichbe`）

## 技术细节

### bat 文件关键点
1. **编码**：Windows cmd 默认使用 GBK/ANSI，不是 UTF-8
2. **行尾符**：必须使用 CRLF (`\r\n`)，不是 LF (`\n`)
3. **转义**：`^` 用于转义特殊字符（如 `>` 需要写成 `^>`）
4. **延迟展开**：使用 `EnableDelayedExpansion` 处理变量

### Python 检测逻辑
```bat
py -3.11 --version    # Windows Python Launcher（推荐）
py -3 --version       # 任意 Python 3.x
python --version      # 直接调用 python
```

### 前端构建验证
```cmd
if not exist "backend\static\index.html" (
  echo [ERROR] Frontend build failed
  exit /b 1
)
```

## 完整流程图

```
Mac 开发环境
    ↓
推送代码到 GitHub
    ↓
触发 GitHub Actions (windows-latest)
    ↓
安装 Node.js → 构建前端 → 验证输出
    ↓
安装 Python → 创建 bat 文件 (Windows 原生)
    ↓
复制后端文件 → 打包 ZIP
    ↓
上传 artifact
    ↓
下载到本地
    ↓
分发给 Windows 用户
    ↓
用户解压 → 双击 START_WINDOWS.bat → 运行成功
```

## 后续优化建议

1. **添加自动测试**：在 workflow 中启动应用并验证 health endpoint
2. **多版本支持**：同时构建 Python 3.11 和 3.12 版本
3. **包含依赖**：预装 Python 依赖到 zip 中（减少首次启动时间）
4. **自动更新**：添加版本检测和自动更新脚本

## 参考资料

- GitHub Actions 文档：https://docs.github.com/actions
- Windows bat 脚本参考：https://ss64.com/nt/
- Python Windows 安装：https://www.python.org/downloads/windows/
