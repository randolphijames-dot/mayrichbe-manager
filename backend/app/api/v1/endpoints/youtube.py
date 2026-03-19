"""YouTube OAuth 授权绑定 API"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account, Platform
from app.models.oauth_state import OAuthState
from app.services.youtube_publisher import build_oauth_flow, YouTubePublisher
from app.core.config import settings

router = APIRouter(prefix="/youtube", tags=["YouTube OAuth"])


@router.get("/oauth/start/{account_id}")
def start_oauth(account_id: int, db: Session = Depends(get_db)):
    """开始 YouTube OAuth 授权流程，返回授权 URL"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.platform == Platform.YOUTUBE,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="YouTube 账号不存在")

    flow = build_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # 保存 state 与 account_id 的关联（数据库存储，10分钟过期）
    OAuthState.create_state(db, state, account_id, ttl_minutes=10)
    # 清理过期的 state
    OAuthState.cleanup_expired(db)
    return {"auth_url": auth_url, "state": state}


@router.get("/oauth/callback")
def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """OAuth 回调：接收 code，换取 Token，保存到账号"""
    account_id = OAuthState.get_account_id(db, state)
    if account_id is None:
        raise HTTPException(status_code=400, detail="无效或过期的 OAuth state，请重新授权")

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    try:
        flow = build_oauth_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        account.yt_oauth_token = json.dumps(token_data)

        # 自动获取并保存 Channel ID
        publisher = YouTubePublisher(account.yt_oauth_token)
        channel = publisher.get_channel_info()
        account.yt_channel_id = channel["id"]
        account.name = account.name or channel["snippet"]["title"]

        db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth 授权失败: {str(e)}")

    # 回调成功后跳转到前端
    return RedirectResponse(url=f"/?oauth_success=1&account_id={account_id}")


@router.get("/channel-info/{account_id}")
def get_channel_info(account_id: int, db: Session = Depends(get_db)):
    """获取 YouTube 频道信息"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.platform == Platform.YOUTUBE,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not account.yt_oauth_token:
        raise HTTPException(status_code=400, detail="该账号未授权 YouTube OAuth，请先授权")

    try:
        publisher = YouTubePublisher(account.yt_oauth_token)
        return publisher.get_channel_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
