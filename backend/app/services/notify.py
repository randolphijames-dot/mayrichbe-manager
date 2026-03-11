"""发布结果通知服务：支持 Line Notify 和 Telegram Bot"""
import requests
from typing import Optional
from app.core.config import settings


def notify_publish_success(
    account_username: str,
    platform: str,
    post_url: str,
    material_title: Optional[str] = None,
):
    """发布成功通知"""
    emoji = "📸" if platform == "instagram" else "▶️"
    message = (
        f"✅ 发布成功\n"
        f"{emoji} 账号：{account_username}\n"
        f"📄 素材：{material_title or '未命名'}\n"
        f"🔗 链接：{post_url}"
    )
    _send_all(message)


def notify_publish_failed(
    account_username: str,
    platform: str,
    error: str,
    retry_count: int = 0,
):
    """发布失败通知"""
    emoji = "📸" if platform == "instagram" else "▶️"
    message = (
        f"❌ 发布失败\n"
        f"{emoji} 账号：{account_username}\n"
        f"⚠️ 错误：{error[:100]}\n"
        f"🔄 已重试：{retry_count} 次"
    )
    _send_all(message)


def notify_account_suspended(account_username: str, platform: str):
    """账号封禁通知"""
    message = f"🚨 账号异常\n账号 {account_username}（{platform}）可能被封禁或限流，请立即检查！"
    _send_all(message)


def _send_all(message: str):
    """向所有配置的渠道发送通知"""
    if settings.LINE_NOTIFY_TOKEN:
        _send_line(message)
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        _send_telegram(message)


def _send_line(message: str):
    """Line Notify 推送"""
    try:
        requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {settings.LINE_NOTIFY_TOKEN}"},
            data={"message": f"\nSocial Manager\n{message}"},
            timeout=10,
        )
    except Exception as e:
        print(f"[Notify] Line 推送失败: {e}")


def _send_telegram(message: str):
    """Telegram Bot 推送"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": f"📱 Social Manager\n\n{message}",
                "parse_mode": "HTML",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[Notify] Telegram 推送失败: {e}")
