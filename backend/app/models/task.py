"""发布任务数据模型"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SAEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"       # 等待执行
    QUEUED = "queued"         # 已入队（Celery）
    RUNNING = "running"       # 执行中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    RETRYING = "retrying"     # 重试中
    CANCELLED = "cancelled"   # 已取消


class PublishTask(Base):
    __tablename__ = "publish_tasks"

    id = Column(Integer, primary_key=True, index=True)

    # 关联
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    account = relationship("Account", back_populates="tasks")
    material = relationship("Material", back_populates="tasks")

    # 调度设置
    scheduled_at = Column(DateTime, nullable=False, comment="计划发布时间（UTC）")
    actual_executed_at = Column(DateTime, nullable=True, comment="实际执行时间")
    random_offset_minutes = Column(Integer, default=0, comment="随机偏移分钟数（防检测）")

    # 状态
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    celery_task_id = Column(String(200), nullable=True, comment="Celery Task ID")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # 结果
    result_post_id = Column(String(200), nullable=True, comment="发布成功后平台返回的 post ID")
    result_url = Column(String(500), nullable=True, comment="发布成功后的帖子 URL")
    error_message = Column(Text, nullable=True)

    # 元信息
    notes = Column(Text, nullable=True)
    is_draft = Column(Boolean, default=False, comment="是否为草稿（不执行）")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联日志
    logs = relationship("PublishLog", back_populates="task", lazy="dynamic")

    def __repr__(self):
        return f"<PublishTask {self.id}: account={self.account_id} status={self.status}>"
