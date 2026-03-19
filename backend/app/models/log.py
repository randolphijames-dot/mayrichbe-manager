"""发布日志数据模型"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class PublishLog(Base):
    __tablename__ = "publish_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 关联
    task_id = Column(Integer, ForeignKey("publish_tasks.id"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    task = relationship("PublishTask", back_populates="logs")
    account = relationship("Account", back_populates="logs")

    # 日志内容
    level = Column(SAEnum(LogLevel), default=LogLevel.INFO)
    event = Column(String(100), nullable=False, comment="事件类型，如 publish_start / publish_success / login_fail")
    message = Column(Text, nullable=False)
    detail = Column(Text, nullable=True, comment="详细信息（JSON 字符串或 traceback）")

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<PublishLog {self.id}: [{self.level}] {self.event}>"
