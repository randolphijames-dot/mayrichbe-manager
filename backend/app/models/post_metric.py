"""作品表现快照模型（发布后数据统计）"""
from datetime import datetime, date

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class PostMetricSnapshot(Base):
    __tablename__ = "post_metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("publish_tasks.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)

    platform = Column(String(20), nullable=False, index=True, comment="instagram / youtube")
    post_id = Column(String(200), nullable=True, comment="平台作品 ID")
    post_url = Column(String(500), nullable=True)

    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)

    snapshot_date = Column(Date, default=date.today, index=True)
    snapshot_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("PublishTask", lazy="joined")
    account = relationship("Account", lazy="joined")
    material = relationship("Material", lazy="joined")

    def __repr__(self):
        return f"<PostMetricSnapshot task={self.task_id} date={self.snapshot_date} views={self.views}>"
