# Mayrichbe Manager 开发记忆

## 📌 项目概况

**项目名称**：Mayrichbe Manager
**功能定位**：Instagram & YouTube 多账号批量管理系统
**技术栈**：
- 后端：FastAPI + SQLite + APScheduler
- 前端：Vue.js + Vite
- 自动化：AdsPower (Instagram) + YouTube API (OAuth)
- 加密：AES-256

---

## 🎯 开发历程

### 第一阶段：Windows 打包尝试（失败）

**目标**：将 Mac 开发的项目打包成 Windows exe 发给朋友

**尝试方案**：
1. GitHub Actions + PyInstaller 打包
2. 遇到的问题：
   - 前端 dist 目录路径错误（vite 直接构建到 backend/static）
   - package.json 缺少 repository 字段
   - PyInstaller 模块导入失败（字符串形式导入不支持）
   - 静态文件路径在打包后环境中找不到
   - `{"detail":"Not Found"}` 错误反复出现

**结论**：PyInstaller 打包 FastAPI 项目太复杂，整整一天未解决

### 第二阶段：转向 Web 版本（成功）

**决策**：暂时放弃 exe 打包，改用浏览器访问的 web 版本

**创建的启动脚本**：
- `START_WINDOWS.bat`：Windows 双击启动
- `START_MAC.command`：Mac 双击启动

**优势**：
- 无需打包，直接运行 Python 代码
- 跨平台统一体验
- 数据库和上传文件可直接复制迁移

---

## 🐛 代码验收与修复

### 发现的问题（共 26 个）

#### 严重问题（6 个）✅ 已修复

1. **scheduler.py - 模型名错误**
   ```python
   # Before
   task = db.query(ScheduledTask).filter(...)
   # After
   task = db.query(PublishTask).filter(...)
   ```

2. **scheduler.py - 参数名不匹配**
   ```python
   # Before
   publisher_fn = publish_video if material.file_type == "video"
   # After
   publisher_fn = publish_video if material.material_type == "video"
   ```

3. **scheduler.py - 密码参数传递错误**
   ```python
   # Before
   password = safe_decrypt(account.ins_password_encrypted)
   result = publisher_fn(..., password=password)
   # After
   result = publisher_fn(..., password_encrypted=account.ins_password_encrypted)
   ```

4. **youtube.py - OAuth 状态存储不持久**
   - 问题：使用内存字典 `_pending_oauth` 存储，重启丢失
   - 解决：创建 `OAuthState` 数据库模型，持久化存储
   ```python
   # Before
   _pending_oauth: dict = {}
   _pending_oauth[state] = account_id
   # After
   from app.models.oauth_state import OAuthState
   OAuthState.create_state(db, state, account_id)
   ```

5. **inbox.py - 缓存无大小限制**
   - 问题：无限增长可能导致内存溢出
   - 解决：添加 `MAX_CACHE_SIZE = 100` 限制

6. **依赖混乱 - Celery/Redis 已废弃**
   - 问题：docker-compose.yml 仍包含 Redis、Celery 服务
   - 解决：删除 Redis/Celery，统一使用 APScheduler

#### 最新修复（2024-03-11）

7. **accounts.py - 账号创建 500 错误**
   ```python
   # 问题：缺少 encrypt 函数导入
   # 修复：添加导入
   from app.core.encryption import encrypt, safe_decrypt
   ```

---

## 🏗️ 架构变更

### Celery/Redis → APScheduler

**原因**：
- Celery 需要 Redis 中间件，增加部署复杂度
- 朋友使用场景简单，不需要分布式任务队列

**变更内容**：
- 删除 `docker-compose.yml` 中的 Redis、Celery worker、Celery beat 服务
- 使用 APScheduler 替代 Celery 的定时任务功能
- 在 `app/main.py` 的 lifespan 钩子中启动调度器
- 恢复数据库中未执行的定时任务

**优势**：
- 零外部依赖（只需 Python + SQLite）
- 启动速度快
- 适合单机部署

---

## 📁 重要文件说明

### 启动脚本

**START_WINDOWS.bat**
```bat
# 自动创建虚拟环境 .venv
# 安装依赖（首次启动）
# 启动后端服务器
# 自动打开浏览器 http://localhost:8000
```

**START_MAC.command**
```bash
# 同上，Mac 版本
```

### 数据备份

**关键文件**：
- `backend/social_manager.db`：SQLite 数据库（账号、素材、任务记录）
- `backend/uploads/`：上传的视频/图片素材

**迁移方法**：
复制这两个文件/文件夹到新电脑，重新启动即可

---

## 🔧 当前状态

**版本**：Web 应用版本（localhost:8000）
**数据库**：SQLite（backend/social_manager.db）
**调度器**：APScheduler（内存 + 数据库持久化）
**前端**：已构建到 backend/static/

**已验证功能**：
- ✅ 账号管理（创建/列表/编辑/删除）
- ✅ 素材上传
- ✅ 定时发布任务调度
- ✅ Instagram 自动发布（AdsPower + Playwright）
- ✅ YouTube 自动发布（官方 API + OAuth）
- ✅ 密码加密存储

**待测试**：
- 🔄 账号创建（刚修复 500 错误，需验证）

---

## 💡 经验教训

1. **打包工具选择**
   - PyInstaller 打包 FastAPI 项目坑太多
   - 简单场景优先考虑 Web 版本（浏览器访问）

2. **架构简化**
   - 不需要分布式就不要引入 Redis/Celery
   - APScheduler + SQLite 足够应对单机场景

3. **测试优先**
   - 开发新功能前先运行一遍代码验收
   - 避免累积太多隐藏 bug

4. **数据迁移**
   - SQLite 文件 + uploads 文件夹 = 完整数据
   - 跨电脑迁移只需复制这两个东西

---

## 📝 下一步计划

- [ ] 完成 Web 版本功能测试
- [ ] 编写用户使用文档（`使用说明.md` 已创建）
- [ ] 考虑后续是否继续尝试 exe 打包（优先级低）
- [ ] 可选：Docker 镜像打包（避免 Python 环境问题）

---

**最后更新**：2024-03-11
**维护者**：Claude Code（导师模式）
