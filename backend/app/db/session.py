"""数据库会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

# 创建引擎
engine = create_engine(
    settings.DATABASE_URL,
    # SQLite 需要 connect_args，PostgreSQL 不需要
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=settings.DB_ECHO,
    pool_pre_ping=True,  # 自动检测断线重连
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入用的数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
