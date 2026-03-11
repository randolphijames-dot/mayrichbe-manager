"""
自动截流服务：按关键词 / 对标账号的粉丝，自动点赞 + 评论引流
风险等级：中高。必须严格限制频率，建议每账号每天最多 10 个互动。
"""
import time
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 每个账号每次截流任务的互动上限（防封号硬限制）
MAX_INTERACTIONS_PER_RUN = 10
# 每次互动之间的最小间隔（秒）
MIN_INTERVAL_BETWEEN_ACTIONS = 30
MAX_INTERVAL_BETWEEN_ACTIONS = 90


def _get_client(account):
    from app.services.instagrapi_publisher import _get_client as base_get_client
    from app.core.encryption import safe_decrypt
    password = safe_decrypt(account.ins_password_encrypted)
    if not password:
        raise RuntimeError(f"账号 {account.username} 未保存密码")
    totp = safe_decrypt(account.ins_totp_secret_encrypted) if account.ins_totp_secret_encrypted else None
    return base_get_client(account.id, account.username, password, account.proxy, totp)


def traffic_by_hashtag(
    account,
    hashtag: str,
    action: str = "like",             # "like" 或 "comment"
    comment_text: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """
    通过话题标签找帖子，然后对这些帖子点赞或评论。
    
    Args:
        hashtag: 话题标签（不含 #，如 "日本財経"）
        action: "like"=点赞 / "comment"=评论
        comment_text: 评论内容，支持从列表随机选一条（用 | 分隔）
        limit: 本次最多互动帖子数（不超过 MAX_INTERACTIONS_PER_RUN）
    """
    limit = min(limit, MAX_INTERACTIONS_PER_RUN)
    done = 0
    errors = 0
    results = []

    try:
        cl = _get_client(account)
        logger.info(f"[{account.username}] 开始 #{hashtag} 截流（action={action}, limit={limit}）")

        # 拉取话题下的最新帖子
        medias = cl.hashtag_medias_recent(hashtag, amount=limit * 3)
        random.shuffle(medias)  # 随机化，避免每次访问相同帖子

        for media in medias:
            if done >= limit:
                break

            # 跳过自己的帖子
            if str(media.user.pk) == str(cl.user_id):
                continue

            try:
                if action == "like":
                    if not media.has_liked:
                        cl.media_like(media.id)
                        results.append({"action": "like", "post": str(media.code), "user": media.user.username})
                        logger.info(f"[{account.username}] 点赞 @{media.user.username} 的帖子 {media.code}")
                        done += 1
                elif action == "comment" and comment_text:
                    # 支持多条话术随机轮换（用 | 分隔）
                    texts = [t.strip() for t in comment_text.split("|") if t.strip()]
                    chosen = random.choice(texts) if texts else comment_text
                    cl.media_comment(media.id, chosen)
                    results.append({"action": "comment", "post": str(media.code), "user": media.user.username, "text": chosen})
                    logger.info(f"[{account.username}] 评论 @{media.user.username}: {chosen[:20]}")
                    done += 1

                # 动作间随机等待（模拟真人节奏）
                wait = random.uniform(MIN_INTERVAL_BETWEEN_ACTIONS, MAX_INTERVAL_BETWEEN_ACTIONS)
                logger.info(f"[{account.username}] 等待 {int(wait)}s 后继续...")
                time.sleep(wait)

            except Exception as e:
                errors += 1
                logger.warning(f"[{account.username}] 互动失败（{media.code}）: {e}")
                if errors >= 3:
                    logger.error(f"[{account.username}] 连续失败 3 次，终止截流")
                    break
                time.sleep(random.uniform(10, 20))

    except Exception as e:
        logger.error(f"traffic_by_hashtag 失败 {account.username}: {e}")

    return {"account": account.username, "hashtag": hashtag, "done": done, "errors": errors, "results": results}


def traffic_by_competitor(
    account,
    competitor_username: str,
    action: str = "like",
    comment_text: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """
    截流：找对标账号的粉丝，去给他们的最近帖子点赞或评论。
    
    Args:
        competitor_username: 对标账号用户名（不含 @）
        action: "like" 或 "comment"
        comment_text: 评论话术（支持 | 分隔多条随机选）
        limit: 本次最多互动人数
    """
    limit = min(limit, MAX_INTERACTIONS_PER_RUN)
    done = 0
    errors = 0
    results = []

    try:
        cl = _get_client(account)
        logger.info(f"[{account.username}] 开始截流对标账号 @{competitor_username}（limit={limit}）")

        competitor_id = cl.user_id_from_username(competitor_username)
        followers = cl.user_followers(competitor_id, amount=limit * 5)
        follower_list = list(followers.values())
        random.shuffle(follower_list)

        for follower in follower_list:
            if done >= limit:
                break
            if str(follower.pk) == str(cl.user_id):
                continue

            try:
                # 找对方最近发的帖子
                user_medias = cl.user_medias(follower.pk, amount=2)
                if not user_medias:
                    continue

                target_media = user_medias[0]

                if action == "like":
                    if not target_media.has_liked:
                        cl.media_like(target_media.id)
                        results.append({"action": "like", "post": str(target_media.code), "user": follower.username})
                        logger.info(f"[{account.username}] 点赞 @{follower.username} 的帖子")
                        done += 1
                elif action == "comment" and comment_text:
                    texts = [t.strip() for t in comment_text.split("|") if t.strip()]
                    chosen = random.choice(texts) if texts else comment_text
                    cl.media_comment(target_media.id, chosen)
                    results.append({"action": "comment", "post": str(target_media.code), "user": follower.username, "text": chosen})
                    logger.info(f"[{account.username}] 评论 @{follower.username}: {chosen[:20]}")
                    done += 1

                wait = random.uniform(MIN_INTERVAL_BETWEEN_ACTIONS, MAX_INTERVAL_BETWEEN_ACTIONS)
                time.sleep(wait)

            except Exception as e:
                errors += 1
                logger.warning(f"[{account.username}] 互动失败（@{follower.username}）: {e}")
                if errors >= 3:
                    logger.error(f"[{account.username}] 连续失败 3 次，终止截流")
                    break
                time.sleep(random.uniform(10, 20))

    except Exception as e:
        logger.error(f"traffic_by_competitor 失败 {account.username}: {e}")

    return {"account": account.username, "competitor": competitor_username, "done": done, "errors": errors, "results": results}
