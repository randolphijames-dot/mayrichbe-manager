"""账号健康检测任务"""
from datetime import datetime, timezone
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


def _get_db():
    from app.db.session import SessionLocal
    return SessionLocal()


@celery_app.task(name="app.tasks.health_check.check_account_health")
def check_account_health(account_id: int):
    """检测单个账号状态（是否被封/限流）"""
    from app.models.account import Account, AccountStatus, Platform

    db = _get_db()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return

        new_status = AccountStatus.UNKNOWN

        if account.platform == Platform.INSTAGRAM:
            new_status = _check_instagram_account(account)
        elif account.platform == Platform.YOUTUBE:
            new_status = _check_youtube_account(account)

        account.status = new_status
        account.last_checked_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"账号 {account.username} ({account.platform}) 状态: {new_status}")

    except Exception as e:
        logger.error(f"检测账号 {account_id} 失败: {e}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.health_check.batch_health_check")
def batch_health_check():
    """批量检测所有活跃账号"""
    from app.models.account import Account

    db = _get_db()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        account_ids = [a.id for a in accounts]
        logger.info(f"开始批量健康检测，共 {len(account_ids)} 个账号")

        for account_id in account_ids:
            check_account_health.delay(account_id)

    finally:
        db.close()


def _check_instagram_account(account) -> str:
    """通过 AdsPower + 轻量请求检测 Instagram 账号状态"""
    from app.models.account import AccountStatus
    import requests

    if not account.adspower_profile_id:
        return AccountStatus.UNKNOWN

    try:
        # 通过代理请求 Instagram profile 页面，检查是否被封
        proxies = {}
        if account.proxy:
            proxies = {"http": account.proxy, "https": account.proxy}

        resp = requests.get(
            f"https://www.instagram.com/{account.username}/",
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            },
            proxies=proxies,
            timeout=15,
        )

        if resp.status_code == 200:
            if '"user":null' in resp.text or "Sorry, this page" in resp.text:
                return AccountStatus.SUSPENDED
            return AccountStatus.ACTIVE
        elif resp.status_code == 404:
            return AccountStatus.SUSPENDED
        else:
            return AccountStatus.UNKNOWN

    except Exception as e:
        logger.warning(f"检测 Instagram 账号 {account.username} 异常: {e}")
        return AccountStatus.UNKNOWN


def _check_youtube_account(account) -> str:
    """通过 YouTube API 检测账号状态"""
    from app.models.account import AccountStatus
    from app.services.youtube_publisher import YouTubePublisher

    if not account.yt_oauth_token:
        return AccountStatus.UNKNOWN

    try:
        publisher = YouTubePublisher(account.yt_oauth_token)
        publisher.get_channel_info()
        return AccountStatus.ACTIVE
    except Exception as e:
        logger.warning(f"检测 YouTube 账号 {account.username} 异常: {e}")
        if "disabled" in str(e).lower() or "suspended" in str(e).lower():
            return AccountStatus.SUSPENDED
        return AccountStatus.UNKNOWN
