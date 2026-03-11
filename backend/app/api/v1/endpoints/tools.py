"""工具类 API：养号、通知测试、设置"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db

router = APIRouter(prefix="/tools", tags=["工具"])


class WarmupRequest(BaseModel):
    account_ids: Optional[List[int]] = None  # 空=所有活跃 INS 账号


@router.post("/warmup")
def trigger_warmup(req: WarmupRequest, db: Session = Depends(get_db)):
    """触发养号任务（支持 instagrapi 和浏览器模式）"""
    try:
        import threading
        from app.tasks.warmup import batch_warmup
        threading.Thread(target=batch_warmup, args=(req.account_ids,), daemon=True).start()
        
        count = len(req.account_ids) if req.account_ids else "全部"
        return {"message": f"已触发 {count} 个账号的养号任务", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {e}")


class NotifyTestRequest(BaseModel):
    channel: str  # "line" 或 "telegram"


@router.post("/notify-test")
def test_notification(req: NotifyTestRequest):
    """测试通知配置是否有效"""
    from app.services.notify import _send_line, _send_telegram
    from app.core.config import settings

    if req.channel == "line":
        if not settings.LINE_NOTIFY_TOKEN:
            raise HTTPException(status_code=400, detail="未配置 LINE_NOTIFY_TOKEN")
        _send_line("✅ Social Manager 通知测试成功！")
    elif req.channel == "telegram":
        if not settings.TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=400, detail="未配置 TELEGRAM_BOT_TOKEN")
        _send_telegram("✅ Social Manager 通知测试成功！")
    else:
        raise HTTPException(status_code=400, detail="channel 只能是 line 或 telegram")

    return {"message": f"{req.channel} 通知发送成功"}


@router.get("/settings")
def get_settings():
    """获取当前配置状态（不返回敏感 key 明文）"""
    from app.core.config import settings
    return {
        "has_line_notify": bool(settings.LINE_NOTIFY_TOKEN),
        "has_telegram": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        "has_yt_oauth": bool(settings.YT_CLIENT_ID),
        "adspower_url": settings.ADSPOWER_API_URL,
        "bitbrowser_url": settings.BITBROWSER_API_URL,
        "upload_dir": settings.UPLOAD_DIR,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "default_random_offset_minutes": settings.DEFAULT_RANDOM_OFFSET_MINUTES,
    }
