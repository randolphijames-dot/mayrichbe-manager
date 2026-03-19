"""素材数据模型"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, Enum as SAEnum, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class MaterialType(str, enum.Enum):
    VIDEO = "video"
    IMAGE = "image"
    CAROUSEL = "carousel"  # 多图轮播（INS）


class MaterialStatus(str, enum.Enum):
    PENDING = "pending"     # 待处理
    READY = "ready"         # 就绪
    PROCESSING = "processing"
    ERROR = "error"


# 素材与账号的多对多关联表（指定素材发送给哪些账号）
material_account_association = Table(
    "material_account_map",
    Base.metadata,
    Column("material_id", Integer, ForeignKey("materials.id"), primary_key=True),
    Column("account_id", Integer, ForeignKey("accounts.id"), primary_key=True),
)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=True, comment="素材标题/描述（内部标识用）")
    material_type = Column(SAEnum(MaterialType), nullable=False)
    status = Column(SAEnum(MaterialStatus), default=MaterialStatus.PENDING)

    # 文件信息
    file_path = Column(String(500), nullable=True, comment="本地文件路径或 OSS 路径")
    file_size = Column(BigInteger, nullable=True, comment="文件大小（字节）")
    mime_type = Column(String(100), nullable=True)
    thumbnail_path = Column(String(500), nullable=True, comment="缩略图路径")
    duration_seconds = Column(Integer, nullable=True, comment="视频时长（秒）")

    # 发布内容
    caption = Column(Text, nullable=True, comment="发布文案（INS caption / YT description）")
    yt_title = Column(String(200), nullable=True, comment="YouTube 视频标题")
    yt_tags = Column(Text, nullable=True, comment="YouTube Tags，JSON 数组字符串")
    yt_category_id = Column(String(10), nullable=True, comment="YouTube 分类 ID")
    yt_privacy = Column(String(20), default="public", comment="YouTube 隐私设置: public/private/unlisted")

    # 文件夹标签（按日期/主题分组，如 "2026-03-10"）
    folder_tag = Column(String(50), nullable=True, index=True)

    # 内容标签（JSON数组字符串，如 ["热点", "教程", "促销"]）
    tags = Column(Text, nullable=True, comment="素材标签，JSON数组")

    # 元信息
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联目标账号（多对多）
    target_accounts = relationship(
        "Account",
        secondary=material_account_association,
        backref="materials",
    )

    # 关联任务
    tasks = relationship("PublishTask", back_populates="material", lazy="dynamic")

    def __repr__(self):
        return f"<Material {self.id}: {self.title}>"
