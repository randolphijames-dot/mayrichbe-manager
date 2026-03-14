"""发布后统计 API：播放量/点赞/评论 + 每日排名"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.timezone import now
from app.db.session import get_db
from app.models.post_metric import PostMetricSnapshot
from app.services.analytics_collector import collect_post_metrics

router = APIRouter(prefix="/analytics", tags=["统计分析"])


def _latest_by_task(rows: list[PostMetricSnapshot]) -> dict[int, PostMetricSnapshot]:
    latest: dict[int, PostMetricSnapshot] = {}
    for row in rows:
        prev = latest.get(row.task_id)
        if not prev or row.snapshot_at > prev.snapshot_at:
            latest[row.task_id] = row
    return latest


def _daily_ranking(
    current_rows: list[PostMetricSnapshot],
    prev_rows: list[PostMetricSnapshot],
    limit: int = 20,
) -> list[dict]:
    current = _latest_by_task(current_rows)
    previous = _latest_by_task(prev_rows)
    ranking: list[dict] = []

    for task_id, row in current.items():
        prev = previous.get(task_id)

        # 关键逻辑：每日排名按「当日增量」而非累计值，避免老作品长期霸榜。
        views_delta = max(row.views - (prev.views if prev else 0), 0)
        likes_delta = max(row.likes - (prev.likes if prev else 0), 0)
        comments_delta = max(row.comments - (prev.comments if prev else 0), 0)
        score = views_delta + likes_delta * 20 + comments_delta * 30

        ranking.append({
            "task_id": row.task_id,
            "platform": row.platform,
            "account_id": row.account_id,
            "account_username": row.account.username if row.account else f"#{row.account_id}",
            "material_id": row.material_id,
            "material_title": row.material.title if row.material else f"素材#{row.material_id}",
            "post_url": row.post_url,
            "views": row.views,
            "likes": row.likes,
            "comments": row.comments,
            "views_delta": views_delta,
            "likes_delta": likes_delta,
            "comments_delta": comments_delta,
            "score": score,
        })

    ranking.sort(key=lambda x: (x["score"], x["views_delta"], x["likes_delta"]), reverse=True)
    return ranking[:limit]


@router.post("/refresh")
def refresh_metrics(
    days: int = Query(30, ge=1, le=90, description="回溯最近多少天的已发布任务"),
    limit: int = Query(300, ge=10, le=1000, description="本次最多采集多少条作品"),
    db: Session = Depends(get_db),
):
    """手动触发一次作品数据采集"""
    result = collect_post_metrics(db, lookback_days=days, task_limit=limit)
    return {"ok": True, **result}


@router.get("/summary")
def get_summary(
    days: int = Query(7, ge=3, le=30, description="趋势天数"),
    db: Session = Depends(get_db),
):
    """获取统计总览 + 最近趋势"""
    end_date = now().date()
    start_date = end_date - timedelta(days=days - 1)
    prev_start = start_date - timedelta(days=1)

    recent_rows = (
        db.query(PostMetricSnapshot)
        .filter(PostMetricSnapshot.snapshot_date >= prev_start)
        .filter(PostMetricSnapshot.snapshot_date <= end_date)
        .all()
    )

    # 总览口径：使用全量最新快照；趋势口径：仅使用近期数据。
    all_rows = db.query(PostMetricSnapshot).all()
    latest_rows = list(_latest_by_task(all_rows).values())
    platform_count = {"instagram": 0, "youtube": 0}
    total_views = 0
    total_likes = 0
    total_comments = 0
    last_snapshot_at = None

    for row in latest_rows:
        platform_count[row.platform] = platform_count.get(row.platform, 0) + 1
        total_views += row.views
        total_likes += row.likes
        total_comments += row.comments
        if not last_snapshot_at or row.snapshot_at > last_snapshot_at:
            last_snapshot_at = row.snapshot_at

    trend = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        prev_day = day - timedelta(days=1)
        day_rows = [r for r in recent_rows if r.snapshot_date == day]
        prev_rows = [r for r in recent_rows if r.snapshot_date == prev_day]

        current_map = _latest_by_task(day_rows)
        prev_map = _latest_by_task(prev_rows)

        views_delta = 0
        likes_delta = 0
        comments_delta = 0
        for task_id, row in current_map.items():
            prev = prev_map.get(task_id)
            views_delta += max(row.views - (prev.views if prev else 0), 0)
            likes_delta += max(row.likes - (prev.likes if prev else 0), 0)
            comments_delta += max(row.comments - (prev.comments if prev else 0), 0)

        trend.append({
            "date": day.isoformat(),
            "views_delta": views_delta,
            "likes_delta": likes_delta,
            "comments_delta": comments_delta,
        })

    latest_day_rows = [r for r in recent_rows if r.snapshot_date == end_date]
    prev_day_rows = [r for r in recent_rows if r.snapshot_date == (end_date - timedelta(days=1))]

    return {
        "overview": {
            "tracked_posts": len(latest_rows),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "last_snapshot_at": last_snapshot_at.isoformat() if last_snapshot_at else None,
        },
        "platform_distribution": [
            {"platform": "instagram", "count": platform_count.get("instagram", 0)},
            {"platform": "youtube", "count": platform_count.get("youtube", 0)},
        ],
        "trend": trend,
        "today_top5": _daily_ranking(latest_day_rows, prev_day_rows, limit=5),
    }


@router.get("/daily-ranking")
def get_daily_ranking(
    target_date: Optional[date] = Query(None, description="排名日期，默认今天（北京时间）"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取指定日期作品排名（按当日增量综合分）"""
    day = target_date or now().date()
    prev_day = day - timedelta(days=1)

    day_rows = db.query(PostMetricSnapshot).filter(PostMetricSnapshot.snapshot_date == day).all()
    prev_rows = db.query(PostMetricSnapshot).filter(PostMetricSnapshot.snapshot_date == prev_day).all()
    ranking = _daily_ranking(day_rows, prev_rows, limit=limit)

    return {
        "date": day.isoformat(),
        "count": len(ranking),
        "items": ranking,
    }
