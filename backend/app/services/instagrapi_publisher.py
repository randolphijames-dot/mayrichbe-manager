"""
instagrapi 无浏览器发布器
优点：不需要 AdsPower / 比特浏览器，直接用账号密码操作 Instagram
风险：为非官方方案，建议配合代理使用，控制发布频率（每日 ≤ 3 次）
"""
import os
import json
import time
import random
from pathlib import Path
from typing import Optional

from app.core.encryption import safe_decrypt


# Session 缓存目录（持久化保存，避免每次重复登录和设备指纹变化）
from app.core.config import settings
SESSION_DIR = Path(settings.UPLOAD_DIR).parent / "instagrapi_sessions"
SESSION_DIR.mkdir(exist_ok=True)


def _get_client(account_id: int, username: str, password: str, proxy: Optional[str] = None, totp_secret: Optional[str] = None):
    """
    获取或恢复 instagrapi 客户端。
    优先复用 session（包含设备指纹和登录状态），避免频繁登录触发验证。
    """
    try:
        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired, TwoFactorRequired
    except ImportError:
        raise RuntimeError("instagrapi 未安装，请运行: pip install instagrapi")

    cl = Client()

    # 设置代理
    if proxy:
        cl.set_proxy(proxy)

    # 尝试复用 session（包含了设备指纹、MAC地址、Android ID 和 登录 Cookies）
    session_file = SESSION_DIR / f"{account_id}_session.json"
    logged_in = False
    
    if session_file.exists():
        try:
            cl.load_settings(str(session_file))
            cl.login(username, password)
            logged_in = True
        except LoginRequired:
            logged_in = False
        except Exception:
            logged_in = False

    # session 无效或不存在，重新登录
    if not logged_in:
        try:
            # 此时 cl 内部已经生成了新的随机设备指纹，或者保留了 load_settings 加载的旧指纹
            cl.login(username, password, verification_code=_get_totp_code(totp_secret) if totp_secret else "")
            logged_in = True
        except TwoFactorRequired:
            if not totp_secret:
                raise RuntimeError("账号开启了两步验证，请在账号设置中填写 TOTP 密钥")
            cl.login(username, password, verification_code=_get_totp_code(totp_secret))
            logged_in = True

    if not logged_in:
        raise RuntimeError(f"instagrapi 登录失败：{username}")

    # 统一保存（同时包含了设备指纹和最新的会话 Cookies）
    cl.dump_settings(str(session_file))

    return cl


def _get_totp_code(secret: str) -> str:
    """从 TOTP 密钥生成 6 位验证码"""
    try:
        import pyotp
        return pyotp.TOTP(secret).now()
    except ImportError:
        raise RuntimeError("需要安装 pyotp: pip install pyotp")


def publish_video(
    account_id: int,
    username: str,
    password_encrypted: str,
    file_path: str,
    caption: str,
    proxy: Optional[str] = None,
    totp_secret_encrypted: Optional[str] = None,
) -> str:
    """
    用 instagrapi 发布视频（Reels）。
    返回帖子 URL。
    """
    password = safe_decrypt(password_encrypted)
    if not password:
        raise RuntimeError(f"账号 {username} 未存储密码，无法使用 instagrapi 方式发布")

    totp_secret = safe_decrypt(totp_secret_encrypted) if totp_secret_encrypted else None
    cl = _get_client(account_id, username, password, proxy, totp_secret)

    # 随机延迟（模拟人工操作）
    time.sleep(random.uniform(2, 5))

    try:
        from instagrapi.types import StoryHashtag
        media = cl.clip_upload(
            Path(file_path),
            caption=caption or "",
        )
        post_url = f"https://www.instagram.com/p/{media.code}/"
        return post_url
    except Exception as e:
        raise RuntimeError(f"instagrapi 发布失败: {e}")


def publish_image(
    account_id: int,
    username: str,
    password_encrypted: str,
    file_path: str,
    caption: str,
    proxy: Optional[str] = None,
    totp_secret_encrypted: Optional[str] = None,
) -> str:
    """
    用 instagrapi 发布图片。
    """
    password = safe_decrypt(password_encrypted)
    if not password:
        raise RuntimeError(f"账号 {username} 未存储密码")

    totp_secret = safe_decrypt(totp_secret_encrypted) if totp_secret_encrypted else None
    cl = _get_client(account_id, username, password, proxy, totp_secret)

    time.sleep(random.uniform(2, 5))

    try:
        media = cl.photo_upload(Path(file_path), caption=caption or "")
        return f"https://www.instagram.com/p/{media.code}/"
    except Exception as e:
        raise RuntimeError(f"instagrapi 发布图片失败: {e}")
