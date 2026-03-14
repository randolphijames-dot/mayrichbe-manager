"""
APScheduler 调度引擎（替代 Celery + Redis）
- 任务存储：SQLite（与主数据库同一文件）
- 持久化：重启后自动恢复未执行任务
- 线程池：最多 8 个并发任务（避免同时操作太多账号）
"""
import logging
from datetime import datetime, timedelta
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

    # 标准版统计：每 6 小时采集一次作品播放/点赞/评论快照
    _scheduler.add_job(
        _collect_post_metrics_job,
        trigger="interval",
        hours=6,
        id="collect_post_metrics_6h",
        name="作品数据采集（6小时）",
        replace_existing=True,
        next_run_time=datetime.now(_scheduler.timezone) + timedelta(minutes=3),
    )
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
    from app.models.task import PublishTask, TaskStatus
    from app.models.account import Account
    from app.models.material import Material

    db = SessionLocal()
    try:
        task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
        if not task:
            return

        if task.status not in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRYING):
            return

        account = db.query(Account).filter(Account.id == task.account_id).first()
        material = db.query(Material).filter(Material.id == task.material_id).first()

        if not account or not material:
            task.status = TaskStatus.FAILED
            task.error_message = "账号或素材不存在"
            db.commit()
            return

        task.status = TaskStatus.RUNNING
        task.actual_executed_at = datetime.utcnow()
        task.error_message = None
        db.commit()

        # 根据平台分发
        platform = getattr(account.platform, "value", account.platform)
        if platform == "instagram":
            _publish_instagram(task, account, material, db)
        elif platform == "youtube":
            _publish_youtube(task, account, material, db)
        else:
            task.status = TaskStatus.FAILED
            task.error_message = f"不支持的平台: {account.platform}"
            db.commit()

    except Exception as e:
        logger.error(f"[Scheduler] 任务 #{task_id} 异常: {traceback.format_exc()}")
        try:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)[:500]
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _publish_instagram(task, account, material, db):
    """Instagram 发布逻辑"""
    try:
        from app.models.account import BrowserType
        from app.models.task import TaskStatus
        from app.models.material import MaterialType
        from app.core.encryption import safe_decrypt

        # 根据账号配置选择发布引擎
        if account.browser_type == BrowserType.NONE or not account.browser_type:
            # instagrapi 方式（模拟安卓 App）
            from app.services.instagrapi_publisher import publish_video, publish_image
            publisher_fn = (
                publish_video
                if material.material_type in (MaterialType.VIDEO, "video")
                else publish_image
            )

            # instagrapi 路径（传入加密的密码，函数内部会解密）
            post_url = publisher_fn(
                account_id=account.id,
                username=account.username,
                password_encrypted=account.ins_password_encrypted,
                file_path=material.file_path,
                caption=getattr(material, "default_caption", None) or getattr(material, "caption", "") or "",
                proxy=account.proxy,
                totp_secret_encrypted=account.ins_totp_secret_encrypted,
            )
            task.status = TaskStatus.SUCCESS
            task.result_url = post_url
            task.error_message = None
            db.commit()
        else:
            # 指纹浏览器方式（AdsPower / 比特浏览器）
            from app.services.instagram_publisher import InstagramPublisher

            profile_id = account.browser_profile_id or account.adspower_profile_id
            if not profile_id:
                task.status = TaskStatus.FAILED
                task.error_message = f"账号 {account.username} 未配置指纹浏览器 Profile ID"
                db.commit()
                return

            # 优先使用加密密码，退而求其次用备注里明文（兼容旧数据）
            password = safe_decrypt(account.ins_password_encrypted) or account.notes or None
            totp_secret = safe_decrypt(account.ins_totp_secret_encrypted) if account.ins_totp_secret_encrypted else None

            publisher = InstagramPublisher(
                profile_id=profile_id,
                username=account.username,
                password=password,  # 可选：如果浏览器已登录，可以为 None
                totp_secret=totp_secret,
                browser_type=account.browser_type,  # 根据账号选择 AdsPower / BitBrowser
            )

            async def _run():
                async with publisher:
                    return await publisher.publish(material)

            import asyncio
            url = asyncio.run(_run())
            task.status = TaskStatus.SUCCESS
            task.result_url = url
            task.error_message = None
            db.commit()

    except Exception as e:
        from app.models.task import TaskStatus
        task.status = TaskStatus.FAILED
        task.error_message = str(e)[:500]
        db.commit()
        raise


def _publish_youtube(task, account, material, db):
    """YouTube 发布逻辑（复用原有服务）"""
    try:
        from app.models.task import TaskStatus
        from app.services.youtube_publisher import YouTubePublisher
        pub = YouTubePublisher(account.yt_oauth_token)
        result = pub.upload_video(material)
        account.yt_oauth_token = pub.get_updated_token_json()
        task.status = TaskStatus.SUCCESS
        task.result_post_id = result.get("video_id")
        task.result_url = result.get("url")
        task.error_message = None
        db.commit()
    except Exception as e:
        from app.models.task import TaskStatus
        task.status = TaskStatus.FAILED
        task.error_message = str(e)[:500]
        db.commit()
        raise


def _collect_post_metrics_job():
    """后台采集已发布作品的数据快照。"""
    from app.db.session import SessionLocal
    from app.services.analytics_collector import collect_post_metrics

    db = SessionLocal()
    try:
        result = collect_post_metrics(db, lookback_days=30, task_limit=300)
        logger.info(f"[Analytics] 采集完成: {result}")
    except Exception as exc:
        logger.warning(f"[Analytics] 采集失败: {exc}")
    finally:
        db.close()
