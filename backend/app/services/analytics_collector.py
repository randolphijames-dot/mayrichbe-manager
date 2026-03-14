"""发布后作品数据采集服务（播放/点赞/评论）"""
from __future__ import annotations

import re
from datetime import timedelta, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.core.encryption import safe_decrypt
from app.core.timezone import now
from app.models.post_metric import PostMetricSnapshot
from app.models.task import PublishTask, TaskStatus


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _parse_instagram_shortcode(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"/p/([^/?#]+)/?", url)
    if match:
        return match.group(1)
    match = re.search(r"/reel/([^/?#]+)/?", url)
    if match:
        return match.group(1)
    return None


def _parse_youtube_video_id(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.hostname in {"youtu.be"}:
        return parsed.path.strip("/") or None
    if parsed.hostname and "youtube.com" in parsed.hostname:
        query = parse_qs(parsed.query or "")
        if "v" in query and query["v"]:
            return query["v"][0]
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed"}:
            return parts[1]
    return None


def _collect_instagram_metrics(task: PublishTask) -> dict[str, Any]:
    from app.services.instagrapi_publisher import _get_client

    account = task.account
    password = safe_decrypt(account.ins_password_encrypted)
    if not password:
        raise RuntimeError(f"账号 {account.username} 未保存密码")

    totp = safe_decrypt(account.ins_totp_secret_encrypted) if account.ins_totp_secret_encrypted else None
    client = _get_client(account.id, account.username, password, account.proxy, totp)

    shortcode = _parse_instagram_shortcode(task.result_url)
    media = None
    if shortcode:
        media_pk = client.media_pk_from_code(shortcode)
        media = client.media_info(media_pk)
    elif task.result_post_id:
        media = client.media_info(task.result_post_id)
    else:
        raise RuntimeError("缺少 result_url/result_post_id，无法识别 Instagram 作品")

    views = _to_int(getattr(media, "view_count", None) or getattr(media, "play_count", None))
    likes = _to_int(getattr(media, "like_count", None))
    comments = _to_int(getattr(media, "comment_count", None))
    post_id = str(getattr(media, "id", "") or task.result_post_id or "")
    post_url = task.result_url or f"https://www.instagram.com/p/{getattr(media, 'code', '')}/"

    return {
        "platform": "instagram",
        "post_id": post_id or None,
        "post_url": post_url,
        "views": views,
        "likes": likes,
        "comments": comments,
    }


def _collect_youtube_metrics(task: PublishTask) -> dict[str, Any]:
    from app.services.youtube_publisher import YouTubePublisher

    account = task.account
    if not account.yt_oauth_token:
        raise RuntimeError(f"账号 {account.username} 未授权 YouTube")

    video_id = task.result_post_id or _parse_youtube_video_id(task.result_url)
    if not video_id:
        raise RuntimeError("缺少 result_post_id/result_url，无法识别 YouTube 视频")

    publisher = YouTubePublisher(account.yt_oauth_token)
    service = publisher._get_service()
    resp = service.videos().list(part="statistics", id=video_id).execute()
    items = resp.get("items") or []
    if not items:
        raise RuntimeError(f"YouTube 未返回视频数据: {video_id}")

    stats = items[0].get("statistics", {})
    account.yt_oauth_token = publisher.get_updated_token_json()

    return {
        "platform": "youtube",
        "post_id": str(video_id),
        "post_url": task.result_url or f"https://www.youtube.com/watch?v={video_id}",
        "views": _to_int(stats.get("viewCount")),
        "likes": _to_int(stats.get("likeCount")),
        "comments": _to_int(stats.get("commentCount")),
    }


def collect_post_metrics(db: Session, lookback_days: int = 30, task_limit: int = 300) -> dict[str, int]:
    """采集最近成功发布任务的作品表现数据并写入快照。

    说明：
    - 标准版按「快照」存储，不覆盖历史，便于每日排名和趋势计算。
    - 每次采集按任务逐条容错，单个失败不影响全局任务。
    """
    since = datetime.utcnow() - timedelta(days=lookback_days)
    snapshot_at = datetime.utcnow()
    snapshot_date = now().date()

    tasks = (
        db.query(PublishTask)
        .filter(PublishTask.status == TaskStatus.SUCCESS)
        .filter(PublishTask.result_url.isnot(None))
        .filter(PublishTask.updated_at >= since)
        .order_by(PublishTask.updated_at.desc())
        .limit(task_limit)
        .all()
    )

    created = 0
    skipped = 0
    failed = 0

    for task in tasks:
        platform = getattr(task.account.platform, "value", task.account.platform)
        try:
            # 关键逻辑：按平台拆分采集策略，避免单一接口耦合。
            if platform == "instagram":
                metrics = _collect_instagram_metrics(task)
            elif platform == "youtube":
                metrics = _collect_youtube_metrics(task)
            else:
                skipped += 1
                continue

            row = PostMetricSnapshot(
                task_id=task.id,
                account_id=task.account_id,
                material_id=task.material_id,
                platform=metrics["platform"],
                post_id=metrics.get("post_id"),
                post_url=metrics.get("post_url"),
                views=_to_int(metrics.get("views")),
                likes=_to_int(metrics.get("likes")),
                comments=_to_int(metrics.get("comments")),
                snapshot_at=snapshot_at,
                snapshot_date=snapshot_date,
            )
            db.add(row)
            created += 1
        except Exception:
            failed += 1

    db.commit()
    return {"created": created, "failed": failed, "skipped": skipped}
