"""
消息中心服务：拉取所有 INS 账号的评论和私信
支持：拉取评论、拉取私信、回复评论、回复私信
"""
import time
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_client(account):
    """获取账号的 instagrapi 客户端"""
    from app.services.instagrapi_publisher import _get_client as base_get_client
    from app.core.encryption import safe_decrypt

    password = safe_decrypt(account.ins_password_encrypted)
    if not password:
        raise RuntimeError(f"账号 {account.username} 未保存密码")

    totp = safe_decrypt(account.ins_totp_secret_encrypted) if account.ins_totp_secret_encrypted else None
    return base_get_client(account.id, account.username, password, account.proxy, totp)


def fetch_recent_comments(account, limit: int = 30) -> list:
    """
    拉取该账号最近帖子的评论（最多查最近 5 条帖子）
    返回：[{ account_id, account_username, post_id, post_url, commenter, text, created_at, comment_id }]
    """
    results = []
    try:
        cl = _get_client(account)
        user_id = cl.user_id_from_username(account.username)
        medias = cl.user_medias(user_id, amount=5)

        for media in medias:
            try:
                comments = cl.media_comments(media.id, amount=limit // len(medias) + 2)
                for c in comments:
                    results.append({
                        "type": "comment",
                        "account_id": account.id,
                        "account_username": account.username,
                        "post_id": str(media.id),
                        "post_url": f"https://www.instagram.com/p/{media.code}/",
                        "from_username": c.user.username,
                        "from_user_id": str(c.user.pk),
                        "text": c.text,
                        "created_at": c.created_at_utc.isoformat() if c.created_at_utc else "",
                        "comment_id": str(c.pk),
                        "replied": False,
                    })
                time.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.warning(f"拉取 {account.username} 帖子 {media.id} 评论失败: {e}")
                continue

    except Exception as e:
        logger.error(f"fetch_recent_comments 失败 {account.username}: {e}")

    # 按时间倒序
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results[:limit]


def fetch_recent_dm(account, limit: int = 20) -> list:
    """
    拉取该账号的最近私信（DM）列表
    返回：[{ account_id, account_username, thread_id, from_username, text, created_at }]
    """
    results = []
    try:
        cl = _get_client(account)
        threads = cl.direct_threads(amount=limit)
        for thread in threads:
            # 取最新一条消息
            if thread.messages:
                latest = thread.messages[0]
                # 找对方是谁（非自己的用户）
                other_users = [u for u in thread.users if str(u.pk) != str(cl.user_id)]
                from_user = other_users[0].username if other_users else "unknown"
                from_user_id = str(other_users[0].pk) if other_users else ""

                results.append({
                    "type": "dm",
                    "account_id": account.id,
                    "account_username": account.username,
                    "thread_id": str(thread.id),
                    "from_username": from_user,
                    "from_user_id": from_user_id,
                    "text": getattr(latest, "text", "(非文字消息)") or "(非文字消息)",
                    "created_at": latest.timestamp.isoformat() if latest.timestamp else "",
                    "is_seen": thread.is_seen(cl.user_id),
                })
        time.sleep(random.uniform(1, 2))
    except Exception as e:
        logger.error(f"fetch_recent_dm 失败 {account.username}: {e}")

    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results[:limit]


def reply_comment(account, comment_id: str, text: str) -> bool:
    """回复某条评论"""
    try:
        cl = _get_client(account)
        time.sleep(random.uniform(2, 5))
        cl.media_comment(comment_id, text)
        logger.info(f"[{account.username}] 回复评论 {comment_id}: {text[:20]}")
        return True
    except Exception as e:
        logger.error(f"回复评论失败 {account.username}: {e}")
        return False


def reply_dm(account, thread_id: str, text: str) -> bool:
    """回复某条私信"""
    try:
        cl = _get_client(account)
        time.sleep(random.uniform(2, 5))
        cl.direct_send(text, [], thread_ids=[thread_id])
        logger.info(f"[{account.username}] 回复私信 {thread_id}: {text[:20]}")
        return True
    except Exception as e:
        logger.error(f"回复私信失败 {account.username}: {e}")
        return False
