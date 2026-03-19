# Social Manager — INS & YouTube 多账号批量管理系统

支持 30+ 账号的批量定时发布、素材管理、账号健康检测。

## 🚀 快速启动（推荐）

### Windows 用户
1. **双击 `START_WINDOWS.bat`**
2. 等待自动打开浏览器
3. 开始使用！

### Mac 用户
1. **双击 `START_MAC.command`**
2. 等待自动打开浏览器
3. 开始使用！

**首次启动**：
- 会自动安装 Python 依赖（约 2-3 分钟）
- 以后启动只需 5 秒

**访问地址**：http://localhost:8000

---

## 📋 前提条件

- ✅ **Python 3.11+**（[下载地址](https://www.python.org/downloads/)）
- ✅ **AdsPower**（用于 Instagram 发布，[下载地址](https://www.adspower.net/)）

---

## 🛠️ 开发模式启动

```bash
# 前提：安装并运行 AdsPower
./start.sh
```

## Docker 启动

```bash
# 1. 复制并配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 填入 YouTube Client ID/Secret 和 AdsPower API Key

# 2. 构建前端
cd frontend && npm install && npm run build

# 3. 启动
docker compose up -d
```

## 功能模块

| 模块 | 说明 |
|------|------|
| 账号管理 | 新增/编辑/批量 CSV 导入，支持 INS + YouTube |
| 素材库 | 上传视频/图片，设置文案、YouTube 标题、目标账号 |
| 发布日历 | 查看所有任务状态，支持取消/重试 |
| 发布日志 | 详细记录每次发布的成功/失败信息 |

## 账号 CSV 导入格式

```
name,username,platform,proxy,adspower_profile_id,notes
日本財経_01,finance_jp_01,instagram,http://user:pass@1.2.3.4:8080,abc123,主账号
日本財経_YT,finance_jp_yt,youtube,,,YouTube主频道
```

## 环境变量说明（backend/.env）

| 变量 | 说明 |
|------|------|
| `ADSPOWER_API_KEY` | AdsPower 本地 API Key（在 AdsPower 设置中查看） |
| `ADSPOWER_API_URL` | AdsPower 本地 API 地址，默认 `http://local.adspower.net:50325` |
| `YT_CLIENT_ID` | Google Cloud OAuth Client ID |
| `YT_CLIENT_SECRET` | Google Cloud OAuth Client Secret |

## 桌面版安装包（Windows）

Windows 安装包需在 Windows 环境构建（PyInstaller 无法跨平台）。

**方式一：GitHub Actions（推荐）**
1. 将本仓库推送到 GitHub（`main` 或 `master` 分支）
2. 打开仓库 → **Actions** → 选择 **Build Windows** 工作流
3. 点击 **Run workflow** 运行（或推送后自动触发）
4. 完成后在 **Artifacts** 中下载 `mayrichbe-manager-windows`，解压得到 `.exe` 安装包

**方式二：在 Windows 本机构建**
- 安装 Python 3.11、Node.js 20
- 在项目根目录执行：`electron\scripts\build-backend.bat` 打包后端
- 将 `electron\backend-dist\backend_win.exe` 复制到 `backend\backend_win.exe`
- 构建前端后执行：`cd electron && npm run build:win`

**兼容与乱码**：安装包已设置 UTF-8（`PYTHONIOENCODING`、SQLite 路径正斜杠），界面与 Mac 版一致；若遇乱码请确认系统区域为中文或 UTF-8。

## 注意事项

1. Instagram 通过 AdsPower + Playwright 操控浏览器发布，需本地安装并运行 AdsPower
2. YouTube 使用官方 API，首次需对每个账号授权（访问 `/api/v1/youtube/oauth/start/{account_id}`）
3. 30+ YouTube 账号需申请多个 Google Cloud 项目以避免配额限制（每项目 10,000 units/天）
4. 建议为每个 Instagram 账号配置独立代理 IP
