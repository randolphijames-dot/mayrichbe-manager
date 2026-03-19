"""消息中心 API：评论 + 私信集中管理"""
import threading
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.account import Account

router = APIRouter(prefix="/inbox", tags=["消息中心"])

# 内存缓存（避免每次请求都打 API，60 秒内复用）
_cache: dict = {}
_cache_ts: dict = {}
CACHE_TTL = 60  # 秒
MAX_CACHE_SIZE = 100  # 最大缓存条数，防止内存溢出


def _cleanup_cache():
    """清理过期缓存和超出限制的缓存"""
    import time as _time
    # 清理过期
    now = _time.time()
    expired_keys = [k for k, ts in _cache_ts.items() if now - ts > CACHE_TTL]
    for k in expired_keys:
        _cache.pop(k, None)
        _cache_ts.pop(k, None)

    # 如果还是超出限制，删除最旧的
    if len(_cache) > MAX_CACHE_SIZE:
        sorted_keys = sorted(_cache_ts.items(), key=lambda x: x[1])
        to_remove = len(_cache) - MAX_CACHE_SIZE
        for k, _ in sorted_keys[:to_remove]:
            _cache.pop(k, None)
            _cache_ts.pop(k, None)


# ─── 请求/响应模型 ───────────────────────────────

class ReplyRequest(BaseModel):
    account_id: int
    comment_id: Optional[str] = None   # 回复评论
    thread_id: Optional[str] = None    # 回复私信
    text: str


# ─── 拉取消息（异步缓存） ────────────────────────

@router.get("/comments")
def get_all_comments(
    account_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """拉取所有（或指定）账号的最新评论"""
    import time as _time

    accounts = _get_target_accounts(account_id, db)
    all_comments = []

    # 清理过期缓存
    _cleanup_cache()

    for acc in accounts:
        if not acc.ins_password_encrypted:
            continue  # 跳过没密码的账号

        cache_key = f"comments_{acc.id}"
        # 使用缓存
        if cache_key in _cache and (_time.time() - _cache_ts.get(cache_key, 0)) < CACHE_TTL:
            all_comments.extend(_cache[cache_key])
            continue

        try:
            from app.services.inbox_service import fetch_recent_comments
            items = fetch_recent_comments(acc, limit=limit // max(len(accounts), 1) + 5)
            _cache[cache_key] = items
            _cache_ts[cache_key] = _time.time()
            all_comments.extend(items)
        except Exception as e:
            all_comments.append({
                "type": "error",
                "account_id": acc.id,
                "account_username": acc.username,
                "text": f"拉取失败: {str(e)[:100]}",
                "created_at": "",
            })

    # 按时间倒序合并
    all_comments.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return all_comments[:limit]


@router.get("/dm")
def get_all_dm(
    account_id: Optional[int] = None,
    limit: int = 30,
    db: Session = Depends(get_db),
):
    """拉取所有（或指定）账号的最新私信"""
    import time as _time

    accounts = _get_target_accounts(account_id, db)
    all_dm = []

    # 清理过期缓存
    _cleanup_cache()

    for acc in accounts:
        if not acc.ins_password_encrypted:
            continue

        cache_key = f"dm_{acc.id}"
        if cache_key in _cache and (_time.time() - _cache_ts.get(cache_key, 0)) < CACHE_TTL:
            all_dm.extend(_cache[cache_key])
            continue

        try:
            from app.services.inbox_service import fetch_recent_dm
            items = fetch_recent_dm(acc, limit=limit // max(len(accounts), 1) + 3)
            _cache[cache_key] = items
            _cache_ts[cache_key] = _time.time()
            all_dm.extend(items)
        except Exception as e:
            all_dm.append({
                "type": "error",
                "account_id": acc.id,
                "account_username": acc.username,
                "text": f"拉取失败: {str(e)[:100]}",
                "created_at": "",
            })

    all_dm.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return all_dm[:limit]


# ─── 刷新缓存（手动触发） ─────────────────────────

@router.post("/refresh")
def refresh_inbox(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """清除缓存，让下次请求重新拉取"""
    keys_to_clear = [k for k in _cache if account_id is None or k.endswith(f"_{account_id}")]
    for k in keys_to_clear:
        _cache.pop(k, None)
        _cache_ts.pop(k, None)
    return {"cleared": len(keys_to_clear), "message": "缓存已清除，下次请求将重新拉取"}


# ─── 回复接口 ────────────────────────────────────

@router.post("/reply")
def reply_message(req: ReplyRequest, db: Session = Depends(get_db)):
    """回复评论或私信"""
    account = db.query(Account).filter(Account.id == req.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not account.ins_password_encrypted:
        raise HTTPException(status_code=400, detail="该账号未保存密码，无法回复")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="回复内容不能为空")

    def _do_reply():
        if req.comment_id:
            from app.services.inbox_service import reply_comment
            reply_comment(account, req.comment_id, req.text)
        elif req.thread_id:
            from app.services.inbox_service import reply_dm
            reply_dm(account, req.thread_id, req.text)

    # 后台异步执行
    threading.Thread(target=_do_reply, daemon=True).start()
    return {"status": "queued", "message": "回复已发送到队列，稍后执行"}


# ─── 工具函数 ────────────────────────────────────

def _get_target_accounts(account_id: Optional[int], db: Session) -> list:
    if account_id:
        acc = db.query(Account).filter(Account.id == account_id).first()
        return [acc] if acc else []
    return db.query(Account).filter(
        Account.platform == "instagram",
        Account.is_active == True,
    ).all()
