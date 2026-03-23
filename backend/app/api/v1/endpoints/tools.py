"""工具类 API：养号、通知测试、设置"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.account import Account, Platform
from app.api.deps import get_current_user, apply_owner_filter, verify_batch_ownership

router = APIRouter(prefix="/tools", tags=["工具"])


class WarmupRequest(BaseModel):
    account_ids: Optional[List[int]] = None  # 空=当前用户的所有活跃 INS 账号


@router.post("/warmup")
def trigger_warmup(req: WarmupRequest, request: Request, db: Session = Depends(get_db)):
    """触发养号任务（支持 instagrapi 和浏览器模式）"""
    user = get_current_user(request)

    try:
        import threading
        from app.tasks.warmup import batch_warmup

        if req.account_ids:
            # 显式指定账号 → 验证所有权
            verify_batch_ownership(db, Account, req.account_ids, user)
            target_ids = req.account_ids
        else:
            # 未指定 → 查询当前用户的所有活跃 INS 账号
            q = db.query(Account).filter(
                Account.platform == Platform.INSTAGRAM,
                Account.is_active == True,
            )
            q = apply_owner_filter(q, Account, user)
            target_ids = [a.id for a in q.all()]

        threading.Thread(target=batch_warmup, args=(target_ids,), daemon=True).start()

        count = len(target_ids)
        return {"message": f"已触发 {count} 个账号的养号任务", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {e}")


class NotifyTestRequest(BaseModel):
    channel: str  # "line" 或 "telegram"


@router.post("/notify-test")
def test_notification(req: NotifyTestRequest, request: Request):
    """测试通知配置是否有效"""
    get_current_user(request)  # 确认已登录

    from app.services.notify import _send_line, _send_telegram
    from app.core.config import settings

    if req.channel == "line":
        if not settings.LINE_NOTIFY_TOKEN:
            raise HTTPException(status_code=400, detail="未配置 LINE_NOTIFY_TOKEN")
        _send_line("Social Manager 通知测试成功！")
    elif req.channel == "telegram":
        if not settings.TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=400, detail="未配置 TELEGRAM_BOT_TOKEN")
        _send_telegram("Social Manager 通知测试成功！")
    else:
        raise HTTPException(status_code=400, detail="channel 只能是 line 或 telegram")

    return {"message": f"{req.channel} 通知发送成功"}


@router.get("/settings")
def get_settings(request: Request):
    """获取当前配置状态（不返回敏感 key 明文）"""
    get_current_user(request)  # 确认已登录

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


@router.get("/warmup/status")
def get_warmup_status(request: Request, db: Session = Depends(get_db)):
    """查询最近 24 小时批量养号的执行结果"""
    from app.models.log import PublishLog
    from datetime import datetime, timedelta

    user = get_current_user(request)

    # 查最近 24 小时的养号日志
    since = datetime.utcnow() - timedelta(hours=24)
    q = db.query(PublishLog).filter(
        PublishLog.event.in_(["warmup_success", "warmup_error"]),
        PublishLog.created_at >= since,
    )
    q = apply_owner_filter(q, PublishLog, user)
    logs = q.order_by(PublishLog.created_at.desc()).all()

    if not logs:
        return {"has_data": False}

    success_count = sum(1 for l in logs if l.event == "warmup_success")
    error_count = sum(1 for l in logs if l.event == "warmup_error")
    last_time = logs[0].created_at.isoformat() if logs else None

    failed_accounts = [l.message for l in logs if l.event == "warmup_error"]

    return {
        "has_data": True,
        "last_executed_at": last_time,
        "success_count": success_count,
        "error_count": error_count,
        "failed_messages": failed_accounts[:5],  # 最多返回 5 条失败信息
    }


@router.get("/check-proxy")
def check_proxy(proxy_url: str, request: Request):
    """测试代理 IP 是否可用，返回出口 IP"""
    import requests as req_lib

    # 支持 IP:PORT:USER:PASS 格式自动转换
    s = proxy_url.strip()
    if s and not s.startswith(("http://", "https://", "socks5://")):
        parts = s.split(":")
        if len(parts) == 4:
            ip, port, user, pw = parts
            s = f"http://{user}:{pw}@{ip}:{port}"

    try:
        resp = req_lib.get(
            "https://api.ipify.org?format=json",
            proxies={"http": s, "https": s},
            timeout=12,
        )
        ip = resp.json().get("ip", "unknown")
        return {"success": True, "ip": ip}
    except Exception as e:
        return {"success": False, "ip": None, "error": str(e)[:200]}
