"""用户管理端点（admin 权限）"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["用户管理"])


# ─── 权限依赖 ───

def get_current_user(request: Request) -> dict:
    """从 request.state.user 获取当前用户（中间件已写入）"""
    user_info = getattr(request.state, "user", None)
    if not user_info or not user_info.get("user_id"):
        raise HTTPException(status_code=401, detail="未登录")
    return user_info


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """要求当前用户是管理员"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ─── 请求/响应模型 ───

class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool
    is_active: bool
    created_at: str

    # 注意：不用 from_attributes，因为 created_at 需要手动格式化


class CreateUserRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = ""
    is_admin: bool = False

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError("用户名至少 2 个字符")
        if len(v) > 50:
            raise ValueError("用户名最多 50 个字符")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("密码至少 4 个字符")
        return v


class UpdateUserRequest(BaseModel):
    password: Optional[str] = None
    display_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


# ─── 端点 ───

@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """列出所有用户（admin only）"""
    users = db.query(User).order_by(User.id).all()
    return [
        UserOut(
            id=u.id,
            username=u.username,
            display_name=u.display_name or u.username,
            is_admin=u.is_admin,
            is_active=u.is_active,
            created_at=u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
        )
        for u in users
    ]


@router.post("/", response_model=UserOut, status_code=201)
def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """创建新用户（admin only）"""
    # 检查用户名唯一
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"用户名 '{req.username}' 已存在")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=req.display_name or req.username,
        is_admin=req.is_admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "",
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    req: UpdateUserRequest,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_user),
):
    """
    修改用户：
    - admin 可改任何人的所有字段
    - 普通用户只能改自己的密码
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    is_admin = current.get("is_admin", False)
    is_self = current["user_id"] == user_id

    # 非 admin 只能改自己的密码
    if not is_admin:
        if not is_self:
            raise HTTPException(status_code=403, detail="无权修改其他用户")
        # 只允许改密码
        if req.display_name is not None or req.is_admin is not None or req.is_active is not None:
            raise HTTPException(status_code=403, detail="普通用户只能修改自己的密码")

    # 应用修改
    if req.password is not None:
        if len(req.password) < 4:
            raise HTTPException(status_code=400, detail="密码至少 4 个字符")
        user.password_hash = hash_password(req.password)
    if req.display_name is not None and is_admin:
        user.display_name = req.display_name
    if req.is_admin is not None and is_admin:
        user.is_admin = req.is_admin
    if req.is_active is not None and is_admin:
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)

    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "",
    )


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """软删除用户（admin only，不能删自己）"""
    if admin["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = False
    db.commit()

    return {"detail": f"用户 '{user.username}' 已禁用"}
