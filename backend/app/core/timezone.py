"""统一时区处理 - 全部使用北京时间（+8）"""
from datetime import datetime, timezone, timedelta

# 北京时区 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))


def now():
    """获取当前北京时间（带时区）"""
    return datetime.now(BEIJING_TZ)


def now_naive():
    """获取当前北京时间（不带时区）"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


def make_aware(dt: datetime):
    """将无时区的 datetime 标记为北京时间"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BEIJING_TZ)
    return dt
