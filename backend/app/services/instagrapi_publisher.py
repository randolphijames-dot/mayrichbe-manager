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


def _get_client(account_id: int, username: str, password: Optional[str] = None, proxy: Optional[str] = None, totp_secret: Optional[str] = None, session_id: Optional[str] = None):
    """
    获取或恢复 instagrapi 客户端。
    优先级：session_id（浏览器导入）> 本地 session 文件 > 密码登录
    """
    try:
        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired, TwoFactorRequired
    except ImportError:
        raise RuntimeError("instagrapi 未安装，请运行: pip install instagrapi")

    cl = Client()

    if proxy:
        cl.set_proxy(proxy)

    session_file = SESSION_DIR / f"{account_id}_session.json"

    # 优先级 1：用浏览器导入的 sessionid 直接恢复登录状态（无需密码，免安全验证）
    if session_id:
        try:
            cl.login_by_sessionid(session_id)
            cl.dump_settings(str(session_file))
            return cl
        except Exception:
            pass  # sessionid 失效，降级到密码登录

    # 优先级 2：复用本地 session 文件
    logged_in = False
    if session_file.exists() and password:
        try:
            cl.load_settings(str(session_file))
            cl.login(username, password)
            logged_in = True
        except Exception:
            logged_in = False

    # 优先级 3：密码重新登录
    if not logged_in:
        if not password:
            raise RuntimeError(f"账号 {username} 未配置密码且 Session ID 无效，无法登录")
        try:
            cl.login(username, password, verification_code=_get_totp_code(totp_secret) if totp_secret else "")
            logged_in = True
        except TwoFactorRequired:
            if not totp_secret:
                raise RuntimeError("账号开启了两步验证，请在账号设置中填写 TOTP 密钥")
            cl.login(username, password, verification_code=_get_totp_code(totp_secret))
            logged_in = True
        except Exception as e:
            error_msg = str(e).lower()

            if 'blacklist' in error_msg or 'ip address' in error_msg:
                raise RuntimeError(
                    "⚠️ Instagram 已封禁当前 IP 地址！\n"
                    "建议：\n"
                    "1. 停止使用 instagrapi 24-48 小时\n"
                    "2. 更换 IP 地址或使用代理\n"
                    "3. 改用 BitBrowser 模式\n"
                    "4. 或部署到云端 VPS"
                )

            if 'password' in error_msg and 'incorrect' in error_msg:
                raise RuntimeError(
                    "❌ 密码错误或账号被锁定\n"
                    "建议：\n"
                    "1. 检查账号密码是否正确\n"
                    "2. 用手机登录确认账号状态\n"
                    "3. 可能需要更换 IP"
                )

            if 'challenge' in error_msg or 'checkpoint' in error_msg:
                raise RuntimeError(
                    "⚠️ Instagram 要求安全验证\n"
                    "解决方法：在账号编辑里填入浏览器 Session ID 即可跳过验证\n"
                    "操作：BitBrowser 打开 Instagram → F12 → Application → Cookies → 复制 sessionid"
                )

            raise RuntimeError(f"登录失败: {e}")

    if not logged_in:
        raise RuntimeError(f"instagrapi 登录失败：{username}")

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
    password_encrypted: Optional[str] = None,
    file_path: str = "",
    caption: str = "",
    proxy: Optional[str] = None,
    totp_secret_encrypted: Optional[str] = None,
    session_id_encrypted: Optional[str] = None,
) -> str:
    """
    用 instagrapi 发布视频（Reels）。
    返回帖子 URL。
    """
    password = safe_decrypt(password_encrypted) if password_encrypted else None
    session_id = safe_decrypt(session_id_encrypted) if session_id_encrypted else None

    if not password and not session_id:
        raise RuntimeError(f"账号 {username} 未配置密码或 Session ID，无法发布")

    totp_secret = safe_decrypt(totp_secret_encrypted) if totp_secret_encrypted else None
    cl = _get_client(account_id, username, password, proxy, totp_secret, session_id)

    # 随机延迟（模拟人工操作，防止被检测）
    wait_time = random.uniform(30, 60)
    time.sleep(wait_time)

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
    password_encrypted: Optional[str] = None,
    file_path: str = "",
    caption: str = "",
    proxy: Optional[str] = None,
    totp_secret_encrypted: Optional[str] = None,
    session_id_encrypted: Optional[str] = None,
) -> str:
    """
    用 instagrapi 发布图片。
    """
    password = safe_decrypt(password_encrypted) if password_encrypted else None
    session_id = safe_decrypt(session_id_encrypted) if session_id_encrypted else None

    if not password and not session_id:
        raise RuntimeError(f"账号 {username} 未配置密码或 Session ID，无法发布")

    totp_secret = safe_decrypt(totp_secret_encrypted) if totp_secret_encrypted else None
    cl = _get_client(account_id, username, password, proxy, totp_secret, session_id)

    # 随机延迟（模拟人工操作，防止被检测）
    wait_time = random.uniform(30, 60)
    time.sleep(wait_time)

    try:
        media = cl.photo_upload(Path(file_path), caption=caption or "")
        return f"https://www.instagram.com/p/{media.code}/"
    except Exception as e:
        raise RuntimeError(f"instagrapi 发布图片失败: {e}")
