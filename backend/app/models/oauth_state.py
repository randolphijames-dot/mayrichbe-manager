"""OAuth State 临时存储模型"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base


class OAuthState(Base):
    """存储 OAuth 授权流程的临时 state"""
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, nullable=False, index=True)
    account_id = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @classmethod
    def cleanup_expired(cls, db):
        """清理过期的 state（建议定期调用）"""
        now = datetime.now(timezone.utc)
        db.query(cls).filter(cls.expires_at < now).delete()
        db.commit()

    @classmethod
    def create_state(cls, db, state: str, account_id: int, ttl_minutes: int = 10):
        """创建新的 OAuth state"""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        obj = cls(state=state, account_id=account_id, expires_at=expires_at)
        db.add(obj)
        db.commit()
        return obj

    @classmethod
    def get_account_id(cls, db, state: str) -> int | None:
        """获取并删除 state 对应的 account_id"""
        obj = db.query(cls).filter(
            cls.state == state,
            cls.expires_at > datetime.now(timezone.utc)
        ).first()
        if obj:
            account_id = obj.account_id
            db.delete(obj)
            db.commit()
            return account_id
        return None
