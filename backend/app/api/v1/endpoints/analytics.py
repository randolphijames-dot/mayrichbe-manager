"""发布后统计 API：播放量/点赞/评论 + 每日排名"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.timezone import now
from app.db.session import get_db
from app.models.post_metric import PostMetricSnapshot
from app.services.analytics_collector import collect_post_metrics
from app.api.deps import get_current_user, apply_owner_filter, verify_ownership

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
    request: Request,
    days: int = Query(30, ge=1, le=90, description="回溯最近多少天的已发布任务"),
    limit: int = Query(300, ge=10, le=1000, description="本次最多采集多少条作品"),
    db: Session = Depends(get_db),
):
    """手动触发一次作品数据采集"""
    user = get_current_user(request)
    # collect_post_metrics 内部查询 PublishTask，传入 owner_id 让它只采集当前用户的任务
    owner_id = None if user.get("is_admin") else user["user_id"]
    result = collect_post_metrics(db, lookback_days=days, task_limit=limit, owner_id=owner_id)
    return {"ok": True, **result}


@router.get("/summary")
def get_summary(
    request: Request,
    days: int = Query(7, ge=3, le=30, description="趋势天数"),
    db: Session = Depends(get_db),
):
    """获取统计总览 + 最近趋势"""
    user = get_current_user(request)
    end_date = now().date()
    start_date = end_date - timedelta(days=days - 1)
    prev_start = start_date - timedelta(days=1)

    recent_q = db.query(PostMetricSnapshot).filter(
        PostMetricSnapshot.snapshot_date >= prev_start,
        PostMetricSnapshot.snapshot_date <= end_date,
    )
    recent_q = apply_owner_filter(recent_q, PostMetricSnapshot, user)
    recent_rows = recent_q.all()

    # 总览口径：使用全量最新快照；趋势口径：仅使用近期数据。
    all_q = db.query(PostMetricSnapshot)
    all_q = apply_owner_filter(all_q, PostMetricSnapshot, user)
    all_rows = all_q.all()
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
    request: Request,
    target_date: Optional[date] = Query(None, description="排名日期，默认今天（北京时间）"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取指定日期作品排名（按当日增量综合分）"""
    user = get_current_user(request)
    day = target_date or now().date()
    prev_day = day - timedelta(days=1)

    day_q = db.query(PostMetricSnapshot).filter(PostMetricSnapshot.snapshot_date == day)
    day_q = apply_owner_filter(day_q, PostMetricSnapshot, user)
    day_rows = day_q.all()

    prev_q = db.query(PostMetricSnapshot).filter(PostMetricSnapshot.snapshot_date == prev_day)
    prev_q = apply_owner_filter(prev_q, PostMetricSnapshot, user)
    prev_rows = prev_q.all()

    ranking = _daily_ranking(day_rows, prev_rows, limit=limit)

    return {
        "date": day.isoformat(),
        "count": len(ranking),
        "items": ranking,
    }


@router.get("/metrics-latest")
def get_latest_metrics(request: Request, db: Session = Depends(get_db)):
    """获取所有任务的最新数据快照"""
    user = get_current_user(request)

    # 获取每个任务的最新快照
    from sqlalchemy import func
    subq_base = db.query(
        PostMetricSnapshot.task_id,
        func.max(PostMetricSnapshot.snapshot_at).label('max_snapshot_at')
    )
    subq_base = apply_owner_filter(subq_base, PostMetricSnapshot, user)
    subq = subq_base.group_by(PostMetricSnapshot.task_id).subquery()

    q = (
        db.query(PostMetricSnapshot)
        .join(
            subq,
            (PostMetricSnapshot.task_id == subq.c.task_id) &
            (PostMetricSnapshot.snapshot_at == subq.c.max_snapshot_at)
        )
    )
    q = apply_owner_filter(q, PostMetricSnapshot, user)
    latest_snapshots = q.all()

    return [
        {
            "task_id": s.task_id,
            "account_id": s.account_id,
            "platform": s.platform,
            "views": s.views,
            "likes": s.likes,
            "comments": s.comments,
            "snapshot_at": s.snapshot_at.isoformat() if s.snapshot_at else None,
        }
        for s in latest_snapshots
    ]


@router.post("/metrics/{task_id}/refresh")
def refresh_task_metrics(task_id: int, request: Request, db: Session = Depends(get_db)):
    """手动刷新指定任务的数据（立即采集）"""
    from app.models.task import PublishTask, TaskStatus
    from app.services.analytics_collector import _collect_instagram_metrics, _collect_youtube_metrics
    from datetime import datetime
    from app.core.timezone import now as tz_now
    from fastapi import HTTPException

    user = get_current_user(request)

    # 验证任务所有权
    task = verify_ownership(db, PublishTask, task_id, user)

    if task.status != TaskStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="只能刷新成功发布的任务")

    if not task.result_url:
        raise HTTPException(status_code=400, detail="任务缺少 result_url")

    # 采集数据
    platform = getattr(task.account.platform, "value", task.account.platform)
    try:
        if platform == "instagram":
            metrics = _collect_instagram_metrics(task)
        elif platform == "youtube":
            metrics = _collect_youtube_metrics(task)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

        # 保存快照（继承任务的 owner_id）
        snapshot = PostMetricSnapshot(
            task_id=task.id,
            account_id=task.account_id,
            material_id=task.material_id,
            platform=metrics["platform"],
            post_id=metrics.get("post_id"),
            post_url=metrics.get("post_url"),
            views=metrics.get("views", 0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            snapshot_at=datetime.utcnow(),
            snapshot_date=tz_now().date(),
            owner_id=task.owner_id,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        return {
            "success": True,
            "metrics": {
                "views": snapshot.views,
                "likes": snapshot.likes,
                "comments": snapshot.comments,
                "snapshot_at": snapshot.snapshot_at.isoformat(),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集失败: {str(e)}")
