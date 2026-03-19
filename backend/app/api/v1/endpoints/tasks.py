"""发布任务 API"""
import random
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.task import PublishTask, TaskStatus
from app.schemas.task import TaskCreate, BatchTaskCreate, TaskUpdate, TaskOut

router = APIRouter(prefix="/tasks", tags=["发布任务"])


@router.get("/", response_model=List[TaskOut])
def list_tasks(
    account_id: Optional[int] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """获取任务列表"""
    q = db.query(PublishTask)
    if account_id:
        q = q.filter(PublishTask.account_id == account_id)
    if status:
        q = q.filter(PublishTask.status == status)
    return q.order_by(PublishTask.scheduled_at.asc()).offset(skip).limit(limit).all()


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """创建单个发布任务"""
    task = PublishTask(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)

    # 如果不是草稿，立即入调度队列
    if not task.is_draft:
        _schedule_task(task, db)

    return task


@router.post("/batch", response_model=List[TaskOut], status_code=status.HTTP_201_CREATED)
def create_batch_tasks(payload: BatchTaskCreate, db: Session = Depends(get_db)):
    """批量创建任务：一个素材 × 多个账号（支持随机时间窗口）"""
    from app.core.timezone import now_naive

    # 立即执行模式：使用当前时间，不再叠加随机延迟
    if payload.instant:
        base_time = now_naive()
        effective_random_offset = 0
    else:
        base_time = payload.scheduled_at
        effective_random_offset = payload.random_offset_minutes

    tasks = []
    for account_id in payload.account_ids:
        # 在指定范围内随机偏移，避免同时发布被识别
        # 立即执行模式下 effective_random_offset=0，不再引入额外延迟
        offset_minutes = 0
        if effective_random_offset > 0:
            offset_minutes = random.randint(0, effective_random_offset)

        actual_scheduled = base_time + timedelta(minutes=offset_minutes)

        task = PublishTask(
            account_id=account_id,
            material_id=payload.material_id,
            scheduled_at=actual_scheduled,
            random_offset_minutes=offset_minutes,
            notes=payload.notes,
        )
        db.add(task)
        tasks.append(task)

    db.commit()
    for t in tasks:
        db.refresh(t)
        _schedule_task(t, db)

    return tasks


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    """更新任务（只允许 PENDING 状态的任务修改）"""
    task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in (TaskStatus.PENDING, TaskStatus.FAILED):
        raise HTTPException(status_code=400, detail="只有 pending/failed 状态的任务可以修改")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(task, k, v)

    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """取消任务"""
    task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status in (TaskStatus.SUCCESS, TaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="任务已完成或已取消")

    # 撤销 APScheduler 任务
    try:
        from app.scheduler import cancel_task as sched_cancel
        sched_cancel(task.id)
    except Exception:
        pass

    task.status = TaskStatus.CANCELLED
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/retry", response_model=TaskOut)
def retry_task(task_id: int, db: Session = Depends(get_db)):
    """手动重试失败任务"""
    task = db.query(PublishTask).filter(PublishTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="只有 failed 状态的任务可以重试")

    task.status = TaskStatus.PENDING
    task.error_message = None
    db.commit()
    _schedule_task(task, db)
    db.refresh(task)
    return task


def _schedule_task(task: PublishTask, db: Session):
    """将任务提交到 APScheduler 调度器"""
    from app.core.timezone import now, make_aware
    import logging
    logger = logging.getLogger(__name__)

    try:
        from app.scheduler import schedule_publish_task

        # 统一使用北京时间（+8）
        run_at = make_aware(task.scheduled_at)
        current = now()

        # 先标记为已入队，避免立即执行线程与当前事务互相覆盖状态
        task.status = TaskStatus.QUEUED
        task.error_message = None
        db.commit()

        logger.info(f"[Task #{task.id}] scheduled_at={run_at}, current={current}, diff={(run_at - current).total_seconds()}s")

        if run_at <= current:
            # 已过期，立即以后台线程方式执行
            logger.info(f"[Task #{task.id}] 立即执行（时间已过期）")
            import threading
            from app.scheduler import _run_publish_task
            threading.Thread(target=_run_publish_task, args=(task.id,), daemon=True).start()
        else:
            logger.info(f"[Task #{task.id}] 定时调度到 {run_at}")
            schedule_publish_task(task.id, run_at)
    except Exception as e:
        logger.error(f"[Task #{task.id}] 调度任务失败: {e}", exc_info=True)
        task.status = TaskStatus.FAILED
        task.error_message = f"调度失败: {str(e)}"
        db.commit()
