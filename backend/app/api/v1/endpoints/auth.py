"""认证端点：登录 + 检查 + 当前用户信息（JWT + 数据库）"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, create_access_token, verify_token
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])


# ─── 请求/响应模型 ───

class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    is_admin: bool


class AuthCheckResponse(BaseModel):
    auth_required: bool
    has_username: bool


class UserMeResponse(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool


# ─── 公共函数：供中间件调用 ───

def verify_request_token(token: str) -> Optional[dict]:
    """
    验证请求中的 token，返回 payload dict 或 None。
    优先按 JWT 解析；向后兼容原始密码直接匹配。
    """
    if not token:
        return None

    # 优先尝试 JWT
    payload = verify_token(token)
    if payload and "user_id" in payload:
        return payload

    # 向后兼容：原始密码直接匹配（未迁移的旧 token）
    if settings.ACCESS_PASSWORD and token == settings.ACCESS_PASSWORD:
        return {"user_id": 0, "username": "legacy", "is_admin": True}

    return None


# ─── 端点 ───

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户名 + 密码登录，查数据库 → 返回 JWT"""
    # 查询用户
    user = db.query(User).filter(User.username == (req.username or "")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 JWT（payload 含 user_id、username、is_admin）
    token = create_access_token({
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
    })

    return LoginResponse(
        token=token,
        username=user.username,
        is_admin=user.is_admin,
    )


@router.get("/check", response_model=AuthCheckResponse)
def auth_check(db: Session = Depends(get_db)):
    """告诉前端：是否需要登录（数据库里有用户就需要）"""
    user_count = db.query(User).filter(User.is_active == True).count()
    return AuthCheckResponse(
        auth_required=user_count > 0,
        has_username=True,  # 数据库模式始终需要用户名
    )


@router.get("/me", response_model=UserMeResponse)
def auth_me(request: Request, db: Session = Depends(get_db)):
    """返回当前登录用户的信息（从 JWT 解析）"""
    user_info = getattr(request.state, "user", None)
    if not user_info or not user_info.get("user_id"):
        raise HTTPException(status_code=401, detail="未登录")

    user = db.query(User).filter(User.id == user_info["user_id"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    return UserMeResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        is_admin=user.is_admin,
    )
