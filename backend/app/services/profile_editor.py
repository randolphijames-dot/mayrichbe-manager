"""
账号资料批量编辑服务（instagrapi）
支持：修改简介、更换头像
每次操作后随机延迟，模拟真实用户行为
"""
import time
import random
from pathlib import Path
from typing import Optional


def _get_client(account_id: int, username: str, password: str,
                proxy: Optional[str] = None, totp_secret: Optional[str] = None):
    """复用 instagrapi 的 session 管理（与发布器共享 session）"""
    # 直接复用 instagrapi_publisher 里的 _get_client
    from app.services.instagrapi_publisher import _get_client as _base_get_client
    return _base_get_client(account_id, username, password, proxy, totp_secret)


def update_biography(
    account_id: int,
    username: str,
    password_encrypted: str,
    new_bio: str,
    proxy: Optional[str] = None,
    totp_secret_encrypted: Optional[str] = None,
) -> dict:
    """修改账号简介，返回更新后的简介内容"""
    from app.core.encryption import safe_decrypt
    password = safe_decrypt(password_encrypted)
    if not password:
        raise RuntimeError(f"{username} 未存储密码，无法操作")

    totp = safe_decrypt(totp_secret_encrypted) if totp_secret_encrypted else None
    cl = _get_client(account_id, username, password, proxy, totp)

    # 随机延迟（2-6秒），模拟人工操作
    time.sleep(random.uniform(2, 6))

    try:
        cl.account_edit(biography=new_bio)
        # 读取更新后的资料确认
        info = cl.account_info()
        return {
            "success": True,
            "username": username,
            "biography": info.biography,
        }
    except Exception as e:
        raise RuntimeError(f"修改简介失败 ({username}): {e}")


def update_avatar(
    account_id: int,
    username: str,
    password_encrypted: str,
    image_path: str,
    proxy: Optional[str] = None,
    totp_secret_encrypted: Optional[str] = None,
) -> dict:
    """更换账号头像"""
    from app.core.encryption import safe_decrypt
    password = safe_decrypt(password_encrypted)
    if not password:
        raise RuntimeError(f"{username} 未存储密码，无法操作")

    if not Path(image_path).exists():
        raise RuntimeError(f"头像文件不存在: {image_path}")

    totp = safe_decrypt(totp_secret_encrypted) if totp_secret_encrypted else None
    cl = _get_client(account_id, username, password, proxy, totp)

    time.sleep(random.uniform(3, 8))

    try:
        cl.account_change_picture(Path(image_path))
        info = cl.account_info()
        return {
            "success": True,
            "username": username,
            "profile_pic_url": str(info.profile_pic_url),
        }
    except Exception as e:
        raise RuntimeError(f"更换头像失败 ({username}): {e}")


def get_profile_info(
    account_id: int,
    username: str,
    password_encrypted: str,
    proxy: Optional[str] = None,
) -> dict:
    """获取当前账号资料（简介、粉丝数等）"""
    from app.core.encryption import safe_decrypt
    password = safe_decrypt(password_encrypted)
    if not password:
        raise RuntimeError(f"{username} 未存储密码")

    cl = _get_client(account_id, username, password, proxy)

    try:
        info = cl.account_info()
        return {
            "username": info.username,
            "full_name": info.full_name,
            "biography": info.biography,
            "follower_count": info.follower_count,
            "following_count": info.following_count,
            "media_count": info.media_count,
            "profile_pic_url": str(info.profile_pic_url),
        }
    except Exception as e:
        raise RuntimeError(f"获取资料失败 ({username}): {e}")
