"""FastAPI 应用入口"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.router import api_router


def find_static_dir():
    """智能查找 static 目录（兼容开发/打包/Electron 环境）"""
    candidates = [
        os.environ.get('STATIC_DIR'),
        './static',
        os.path.join(os.getcwd(), 'static'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'static'),
    ]
    # PyInstaller 打包后：static 在 _MEIPASS 或 backend/ 下
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.insert(0, os.path.join(meipass, 'static'))
        base = os.path.dirname(sys.executable)
        candidates.insert(0, os.path.join(base, 'static'))

    for path in candidates:
        if path and os.path.exists(path) and os.path.isdir(path):
            return os.path.abspath(path)

    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭钩子"""
    # 初始化数据库（建表 + 自动迁移）
    from app.db.init_db import init_db
    init_db()
    # 创建上传目录
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # 启动 APScheduler 调度器（替代 Celery/Redis）
    from app.scheduler import start_scheduler, schedule_publish_task
    from app.db.session import SessionLocal
    scheduler = start_scheduler(settings.DATABASE_URL)
    # 恢复数据库里 status=scheduled 但尚未执行的任务
    _restore_pending_tasks(scheduler, schedule_publish_task)
    yield
    # 应用关闭时停止调度器
    from app.scheduler import stop_scheduler
    stop_scheduler()


def _restore_pending_tasks(scheduler, schedule_fn):
    """启动时恢复未执行的定时任务"""
    from app.db.session import SessionLocal
    from app.core.timezone import now, make_aware
    try:
        db = SessionLocal()
        from app.models.task import PublishTask
        pending = db.query(PublishTask).filter(
            PublishTask.status.in_(["pending", "queued"])
        ).all()
        current = now()
        restored = 0
        for task in pending:
            if task.scheduled_at and make_aware(task.scheduled_at) > current:
                try:
                    schedule_fn(task.id, task.scheduled_at)
                    restored += 1
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"恢复任务 #{task.id} 失败: {e}")
        db.close()
        if restored:
            import logging
            logging.getLogger(__name__).info(f"[Startup] 已恢复 {restored} 个待执行任务")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[Startup] 恢复任务失败（可忽略首次启动）: {e}")


app = FastAPI(
    title="Social Manager API",
    description="多账号批量管理系统 - Instagram & YouTube",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS（允许前端开发服务器访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 生产环境可改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 访问密码中间件（可选，设置 ACCESS_PASSWORD 后启用）
@app.middleware("http")
async def access_guard(request, call_next):
    from fastapi.responses import JSONResponse
    password = settings.ACCESS_PASSWORD
    if password and not request.url.path.startswith("/health"):
        token = (
            request.headers.get("X-Access-Token")
            or request.query_params.get("token")
        )
        if token != password:
            return JSONResponse({"detail": "未授权，需要访问密码"}, status_code=401)
    return await call_next(request)

# health check（必须在静态文件 mount 之前注册）
@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

# 注册 API 路由
app.include_router(api_router)

# Uploads 静态文件服务（素材文件访问）
uploads_dir = os.path.abspath(settings.UPLOAD_DIR)
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
    import logging
    logging.getLogger(__name__).info(f"[Main] Uploads目录已挂载: {uploads_dir}")

# 静态文件服务（前端构建产物，挂载在最后，防止拦截 API 路由）
static_dir = find_static_dir()
if static_dir:
    import logging
    logging.getLogger(__name__).info(f"[Main] 静态文件目录: {static_dir}")
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    import logging
    logging.warning(f"[Main] ⚠️ 未找到静态文件目录，前端页面将无法访问")
