"""
APScheduler 调度引擎（替代 Celery + Redis）
- 任务存储：SQLite（与主数据库同一文件）
- 持久化：重启后自动恢复未执行任务
- 线程池：最多 8 个并发任务（避免同时操作太多账号）
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("调度器尚未启动")
    return _scheduler


def start_scheduler(database_url: str):
    """启动 APScheduler（应用启动时调用）"""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    jobstores = {
        "default": SQLAlchemyJobStore(url=database_url, tablename="apscheduler_jobs")
    }
    executors = {
        "default": ThreadPoolExecutor(max_workers=8)
    }
    job_defaults = {
        "coalesce": True,        # 错过多次触发只执行一次
        "max_instances": 1,      # 同一任务不重叠执行
        "misfire_grace_time": 300,  # 延误 5 分钟内仍执行
    }

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="Asia/Tokyo",
    )
    _scheduler.start()
    logger.info("[Scheduler] APScheduler 已启动")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] APScheduler 已停止")


def schedule_publish_task(task_id: int, run_at: datetime):
    """
    将发布任务注册到调度器。
    run_at 应为本地时间（带时区）。
    """
    scheduler = get_scheduler()
    job_id = f"publish_{task_id}"

    # 防止重复注册
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        _run_publish_task,
        trigger="date",
        run_date=run_at,
        id=job_id,
        args=[task_id],
        name=f"发布任务 #{task_id}",
    )
    logger.info(f"[Scheduler] 已注册任务 #{task_id}，执行时间: {run_at}")


def cancel_task(task_id: int):
    """取消已注册的发布任务"""
    scheduler = get_scheduler()
    job_id = f"publish_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"[Scheduler] 已取消任务 #{task_id}")


def _run_publish_task(task_id: int):
    """实际执行发布逻辑（在线程池中运行）"""
    import traceback
    from app.db.session import SessionLocal
    from app.models.task import PublishTask
    from app.models.account import Account
    from app.models.material import Material

    db = SessionLocal()
    try:
        task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
        if not task or task.status not in ("pending", "scheduled"):
            return

        account = db.query(Account).filter(Account.id == task.account_id).first()
        material = db.query(Material).filter(Material.id == task.material_id).first()

        if not account or not material:
            task.status = "failed"
            task.result_message = "账号或素材不存在"
            db.commit()
            return

        task.status = "running"
        db.commit()

        # 根据平台分发
        if account.platform == "instagram":
            _publish_instagram(task, account, material, db)
        elif account.platform == "youtube":
            _publish_youtube(task, account, material, db)
        else:
            task.status = "failed"
            task.result_message = f"不支持的平台: {account.platform}"
            db.commit()

    except Exception as e:
        logger.error(f"[Scheduler] 任务 #{task_id} 异常: {traceback.format_exc()}")
        try:
            task.status = "failed"
            task.result_message = str(e)[:500]
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _publish_instagram(task, account, material, db):
    """Instagram 发布逻辑"""
    try:
        from app.models.account import BrowserType

        # 根据账号配置选择发布引擎
        if account.browser_type == BrowserType.NONE or not account.browser_type:
            # instagrapi 方式（模拟安卓 App）
            from app.services.instagrapi_publisher import publish_video, publish_image
            publisher_fn = publish_video if material.material_type == "video" else publish_image
        else:
            # 指纹浏览器方式（备用）
            from app.services.instagram_publisher import InstagramPublisher
            pub = InstagramPublisher(account, material)
            publisher_fn = pub.publish
            result = publisher_fn()
            task.status = "success" if result.get("success") else "failed"
            task.result_message = result.get("message", "")
            db.commit()
            return

        # instagrapi 路径（传入加密的密码，函数内部会解密）
        result = publisher_fn(
            account_id=account.id,
            username=account.username,
            password_encrypted=account.ins_password_encrypted,
            file_path=material.file_path,
            caption=task.caption or material.default_caption or "",
            proxy=account.proxy,
            totp_secret_encrypted=account.ins_totp_secret_encrypted,
        )
        task.status = "success" if result.get("success") else "failed"
        task.result_message = result.get("message", "")[:500]
        db.commit()

    except Exception as e:
        task.status = "failed"
        task.result_message = str(e)[:500]
        db.commit()
        raise


def _publish_youtube(task, account, material, db):
    """YouTube 发布逻辑（复用原有服务）"""
    try:
        from app.services.youtube_publisher import YouTubePublisher
        pub = YouTubePublisher(account, material, task)
        result = pub.publish()
        task.status = "success" if result.get("success") else "failed"
        task.result_message = result.get("message", "")[:500]
        db.commit()
    except Exception as e:
        task.status = "failed"
        task.result_message = str(e)[:500]
        db.commit()
        raise
