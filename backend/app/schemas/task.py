"""任务相关 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    account_id: int
    material_id: int
    scheduled_at: datetime = Field(..., description="计划发布时间（UTC）")
    random_offset_minutes: int = Field(default=0, ge=0, le=120, description="随机偏移分钟范围（0=不偏移）")
    notes: Optional[str] = None
    is_draft: bool = False


class BatchTaskCreate(BaseModel):
    """批量创建任务：一个素材 × 多个账号"""
    material_id: int
    account_ids: List[int]
    scheduled_at: datetime
    random_offset_minutes: int = Field(default=30, ge=0, le=120)
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    random_offset_minutes: Optional[int] = None
    notes: Optional[str] = None
    is_draft: Optional[bool] = None


class TaskOut(BaseModel):
    id: int
    account_id: int
    material_id: int
    scheduled_at: datetime
    actual_executed_at: Optional[datetime] = None
    random_offset_minutes: int
    status: TaskStatus
    celery_task_id: Optional[str] = None
    retry_count: int
    result_post_id: Optional[str] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    is_draft: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LogOut(BaseModel):
    id: int
    task_id: Optional[int] = None
    account_id: Optional[int] = None
    level: str
    event: str
    message: str
    detail: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
