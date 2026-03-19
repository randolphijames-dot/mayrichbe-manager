# Mayrichbe Manager - Windows Web版使用说明

## 目标
- 在 Windows 电脑上以浏览器访问方式运行。
- 功能与当前项目一致（账号、素材、发布、日志、统计、每日排名）。

## 你只需要做
1. 安装 Python 3.11+（安装时勾选 `Add Python to PATH`）。
2. 解压项目目录。
3. 双击 `START_WINDOWS.bat`。
4. 浏览器打开 `http://127.0.0.1:8000` 即可使用。

## CSV 模板
- 使用 `ACCOUNT_IMPORT_TEMPLATE.csv`（ASCII 文件名，避免 Windows 解压乱码）。

## 首次启动会自动完成
- 创建 `backend/.venv`
- 安装 Python 依赖
- 安装 Playwright Chromium（一次）
- 初始化数据库
- 启动 Web 服务

## 启动失败先做这个
- 双击 `CHECK_WINDOWS_WEB.bat`
- 看 `FAIL`/`WARN` 项并按提示处理

## 与你当前电脑一致体验的关键点
- 使用同一套后端接口和前端静态资源（非裁剪版）。
- 保留全部路由与功能：`/accounts /materials /schedule /calendar /analytics ...`
- 启动后访问入口仍是 `http://127.0.0.1:8000`。

## 数据迁移（保证一致）
从原电脑复制这两个路径到新 Windows 机器同位置：
- `backend/social_manager.db`
- `backend/uploads/`

## 注意
- Instagram 自动发布依赖本地 AdsPower/BitBrowser；未运行时相关功能会失败，但其他功能可用。
- YouTube 发布需要在 `backend/.env` 配置 OAuth。
