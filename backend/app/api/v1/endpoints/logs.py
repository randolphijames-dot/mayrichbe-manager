"""发布日志 API"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.log import PublishLog, LogLevel
from app.schemas.task import LogOut

router = APIRouter(prefix="/logs", tags=["发布日志"])


@router.get("/", response_model=List[LogOut])
def list_logs(
    account_id: Optional[int] = Query(None),
    task_id: Optional[int] = Query(None),
    level: Optional[LogLevel] = Query(None),
    event: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """获取发布日志"""
    q = db.query(PublishLog)
    if account_id:
        q = q.filter(PublishLog.account_id == account_id)
    if task_id:
        q = q.filter(PublishLog.task_id == task_id)
    if level:
        q = q.filter(PublishLog.level == level)
    if event:
        q = q.filter(PublishLog.event == event)
    return q.order_by(PublishLog.created_at.desc()).offset(skip).limit(limit).all()
