"""发布任务（Celery Tasks）"""
import asyncio
import json
from datetime import datetime, timezone
from celery import shared_task
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


def _get_db_session():
    """在 Celery worker 中获取数据库会话"""
    from app.db.session import SessionLocal
    return SessionLocal()


def _write_log(db, task_id: int, account_id: int, level: str, event: str, message: str, detail: str = None):
    """写入发布日志"""
    from app.models.log import PublishLog, LogLevel
    log = PublishLog(
        task_id=task_id,
        account_id=account_id,
        level=level,
        event=event,
        message=message,
        detail=detail,
    )
    db.add(log)
    db.commit()


@celery_app.task(bind=True, name="app.tasks.publish.publish_task", max_retries=3)
def publish_task(self, task_id: int):
    """分发任务到对应平台的发布函数"""
    from app.models.task import PublishTask, TaskStatus
    from app.models.account import Platform

    db = _get_db_session()
    try:
        task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return

        if task.status == TaskStatus.CANCELLED:
            logger.info(f"任务 {task_id} 已取消，跳过")
            return

        platform = task.account.platform
        if platform == Platform.INSTAGRAM:
            publish_instagram_task.apply_async(args=[task_id])
        elif platform == Platform.YOUTUBE:
            publish_youtube_task.apply_async(args=[task_id])
        else:
            logger.error(f"未知平台: {platform}")

    except Exception as e:
        logger.exception(f"分发任务 {task_id} 失败: {e}")
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.publish.publish_instagram_task", max_retries=3)
def publish_instagram_task(self, task_id: int):
    """Instagram 发布任务（含防封号检查）"""
    from app.models.task import PublishTask, TaskStatus
    from app.services.instagram_publisher import InstagramPublisher
    from app.services.human_behavior import cooldown_manager

    db = _get_db_session()
    task = None
    try:
        task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
        if not task:
            return

        account = task.account
        material = task.material

        # 防封号：冷却期检查
        can_post, reason = cooldown_manager.can_post(account.id, "instagram")
        if not can_post:
            task.status = TaskStatus.PENDING
            task.error_message = f"冷却中: {reason}"
            db.commit()
            raise self.retry(exc=RuntimeError(reason), countdown=3600)

        # 更新任务状态
        task.status = TaskStatus.RUNNING
        task.actual_executed_at = datetime.now(timezone.utc)
        db.commit()

        _write_log(db, task_id, account.id, "info", "publish_start",
                   f"开始发布 Instagram: {account.username} (方式: {account.browser_type})")

        # ─── 根据发布方式选择发布器 ───
        browser_type = account.browser_type or "adspower"

        if browser_type == "none":
            # instagrapi 无浏览器模式
            from app.services.instagrapi_publisher import publish_video, publish_image
            from app.models.material import MaterialType
            if material.material_type in (MaterialType.VIDEO, "video"):
                post_url = publish_video(
                    account_id=account.id,
                    username=account.username,
                    password_encrypted=account.ins_password_encrypted or "",
                    file_path=material.file_path,
                    caption=material.caption or "",
                    proxy=account.proxy,
                    totp_secret_encrypted=account.ins_totp_secret_encrypted,
                )
            else:
                post_url = publish_image(
                    account_id=account.id,
                    username=account.username,
                    password_encrypted=account.ins_password_encrypted or "",
                    file_path=material.file_path,
                    caption=material.caption or "",
                    proxy=account.proxy,
                    totp_secret_encrypted=account.ins_totp_secret_encrypted,
                )
        else:
            # 指纹浏览器模式（AdsPower 或 比特浏览器）
            profile_id = account.browser_profile_id or account.adspower_profile_id
            if not profile_id:
                raise ValueError(f"账号 {account.username} 未配置指纹浏览器 Profile ID")

            publisher = InstagramPublisher(
                profile_id=profile_id,
                username=account.username,
                password=account.notes or "",
                browser_type=browser_type,
            )

            async def _publish():
                async with publisher:
                    return await publisher.publish(material)

            post_url = asyncio.run(_publish())
        cooldown_manager.record_post(account.id)

        # 成功
        task.status = TaskStatus.SUCCESS
        task.result_url = post_url
        db.commit()

        _write_log(db, task_id, account.id, "success", "publish_success",
                   f"Instagram 发布成功: {post_url}")
        logger.info(f"Instagram 任务 {task_id} 发布成功: {post_url}")

        # 发布成功通知
        try:
            from app.services.notify import notify_publish_success
            notify_publish_success(account.username, "instagram", post_url, material.title)
        except Exception:
            pass

    except Exception as exc:
        logger.exception(f"Instagram 任务 {task_id} 失败: {exc}")
        if task:
            task.retry_count += 1
            task.error_message = str(exc)

            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.RETRYING
                db.commit()
                # 指数退避重试（5min, 10min, 20min）
                raise self.retry(exc=exc, countdown=300 * (2 ** (task.retry_count - 1)))
            else:
                task.status = TaskStatus.FAILED
                db.commit()
                _write_log(db, task_id, task.account_id, "error", "publish_failed",
                           f"Instagram 发布失败（已重试 {task.retry_count} 次）: {exc}",
                           detail=str(exc))
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.publish.publish_youtube_task", max_retries=3)
def publish_youtube_task(self, task_id: int):
    """YouTube 发布任务"""
    from app.models.task import PublishTask, TaskStatus
    from app.services.youtube_publisher import YouTubePublisher

    db = _get_db_session()
    task = None
    try:
        task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
        if not task:
            return

        account = task.account
        material = task.material

        if not account.yt_oauth_token:
            raise ValueError(f"账号 {account.username} 未授权 YouTube OAuth")

        task.status = TaskStatus.RUNNING
        task.actual_executed_at = datetime.now(timezone.utc)
        db.commit()

        _write_log(db, task_id, account.id, "info", "publish_start",
                   f"开始发布 YouTube: {account.username}")

        publisher = YouTubePublisher(account.yt_oauth_token)
        result = publisher.upload_video(material)

        # 更新刷新后的 Token（避免 Token 过期问题）
        account.yt_oauth_token = publisher.get_updated_token_json()

        task.status = TaskStatus.SUCCESS
        task.result_post_id = result["video_id"]
        task.result_url = result["url"]
        db.commit()

        _write_log(db, task_id, account.id, "success", "publish_success",
                   f"YouTube 发布成功: {result['url']}")
        logger.info(f"YouTube 任务 {task_id} 发布成功: {result['url']}")

        # 发布成功通知
        try:
            from app.services.notify import notify_publish_success
            notify_publish_success(account.username, "youtube", result["url"], material.yt_title or material.title)
        except Exception:
            pass

    except Exception as exc:
        logger.exception(f"YouTube 任务 {task_id} 失败: {exc}")
        if task:
            task.retry_count += 1
            task.error_message = str(exc)

            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.RETRYING
                db.commit()
                raise self.retry(exc=exc, countdown=300 * (2 ** (task.retry_count - 1)))
            else:
                task.status = TaskStatus.FAILED
                db.commit()
                _write_log(db, task_id, task.account_id, "error", "publish_failed",
                           f"YouTube 发布失败: {exc}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.publish.check_and_dispatch_pending")
def check_and_dispatch_pending():
    """兜底检查：把到期的 PENDING 任务重新入队（防止重启后遗漏）"""
    from app.models.task import PublishTask, TaskStatus

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        # 查找计划时间已到但仍是 PENDING 状态的任务
        overdue_tasks = db.query(PublishTask).filter(
            PublishTask.status == TaskStatus.PENDING,
            PublishTask.scheduled_at <= now,
            PublishTask.is_draft == False,
        ).all()

        dispatched = 0
        for task in overdue_tasks:
            try:
                result = publish_task.apply_async(args=[task.id])
                task.celery_task_id = result.id
                task.status = TaskStatus.QUEUED
                dispatched += 1
            except Exception as e:
                logger.error(f"兜底调度任务 {task.id} 失败: {e}")

        if dispatched > 0:
            db.commit()
            logger.info(f"兜底调度：重新入队 {dispatched} 个逾期任务")

    except Exception as e:
        logger.error(f"兜底检查失败: {e}")
    finally:
        db.close()
