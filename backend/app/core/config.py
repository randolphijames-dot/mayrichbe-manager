"""全局配置（从环境变量读取）"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "Social Manager"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "sqlite:///./social_manager.db"
    DB_ECHO: bool = False  # True 时打印 SQL

    # Redis（Celery 用）
    REDIS_URL: str = "redis://localhost:6379/0"

    # 文件存储
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 500  # 最大上传 500MB

    # AdsPower
    ADSPOWER_API_URL: str = "http://local.adspower.net:50325"
    ADSPOWER_API_KEY: Optional[str] = None

    # 比特浏览器（BitBrowser）
    BITBROWSER_API_URL: str = "http://127.0.0.1:54345"

    # YouTube
    YT_CLIENT_ID: Optional[str] = None
    YT_CLIENT_SECRET: Optional[str] = None
    YT_REDIRECT_URI: str = "http://localhost:8000/api/v1/youtube/oauth/callback"

    # 安全
    SECRET_KEY: str = "change-me-in-production-use-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # 发布设置
    DEFAULT_RANDOM_OFFSET_MINUTES: int = 30

    # 通知
    LINE_NOTIFY_TOKEN: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # 访问控制（设置后 API 需要 X-Access-Token 请求头）
    ACCESS_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
