"""账号数据模型"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class Platform(str, enum.Enum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"       # 正常
    SUSPENDED = "suspended" # 被封禁
    LIMITED = "limited"     # 被限流
    UNKNOWN = "unknown"     # 未检测


class BrowserType(str, enum.Enum):
    ADSPOWER = "adspower"       # AdsPower 指纹浏览器
    BITBROWSER = "bitbrowser"   # 比特浏览器
    NONE = "none"               # 不使用指纹浏览器（手动登录）


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="账号显示名")
    username = Column(String(100), nullable=False, comment="平台用户名")
    platform = Column(SAEnum(Platform), nullable=False, comment="平台类型")
    status = Column(SAEnum(AccountStatus), default=AccountStatus.UNKNOWN)

    # 账号分组
    group_name = Column(String(100), nullable=True, comment="账号分组名，如：财经类、生活类")

    # 代理设置
    proxy = Column(String(300), nullable=True, comment="代理地址 格式: http://user:pass@ip:port")

    # 指纹浏览器设置
    browser_type = Column(SAEnum(BrowserType), default=BrowserType.ADSPOWER, comment="指纹浏览器类型")
    browser_profile_id = Column(String(200), nullable=True, comment="指纹浏览器 Profile ID（AdsPower 或 比特浏览器）")

    # 已废弃字段（保留向后兼容）
    adspower_profile_id = Column(String(100), nullable=True)
    adspower_group_id = Column(String(100), nullable=True)

    # Instagram 登录（可选加密存储）
    ins_password_encrypted = Column(Text, nullable=True, comment="INS 密码（AES 加密存储）")
    ins_totp_secret_encrypted = Column(Text, nullable=True, comment="INS 2FA TOTP 密钥（AES 加密）")

    # YouTube OAuth（YouTube 专用）
    yt_oauth_token = Column(Text, nullable=True, comment="YouTube OAuth2 Token JSON")
    yt_channel_id = Column(String(100), nullable=True, comment="YouTube Channel ID")

    # 元信息
    notes = Column(Text, nullable=True, comment="备注")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked_at = Column(DateTime, nullable=True, comment="上次健康检测时间")

    # 关联
    tasks = relationship("PublishTask", back_populates="account", lazy="dynamic")
    logs = relationship("PublishLog", back_populates="account", lazy="dynamic")

    def __repr__(self):
        return f"<Account {self.platform.value}:{self.username}>"
