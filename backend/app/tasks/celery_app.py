"""Celery 应用配置"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "social_manager",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.publish",
        "app.tasks.health_check",
    ],
)

celery_app.conf.update(
    # 时区设置
    timezone="Asia/Tokyo",
    enable_utc=True,

    # 序列化
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 任务路由（按平台分到不同 worker 队列）
    task_routes={
        "app.tasks.publish.publish_instagram_task": {"queue": "instagram"},
        "app.tasks.publish.publish_youtube_task": {"queue": "youtube"},
        "app.tasks.publish.publish_task": {"queue": "default"},
        "app.tasks.health_check.*": {"queue": "health"},
    },

    # 重试设置
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 结果过期时间 7 天
    result_expires=7 * 24 * 3600,

    # 定时任务（Celery Beat）
    beat_schedule={
        # 每分钟检查待执行任务（兜底机制）
        "check-pending-tasks": {
            "task": "app.tasks.publish.check_and_dispatch_pending",
            "schedule": 60.0,
        },
        # 每天凌晨 2 点批量健康检测
        "daily-health-check": {
            "task": "app.tasks.health_check.batch_health_check",
            "schedule": crontab(hour=2, minute=0),
        },
    },
)
