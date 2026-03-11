"""批量账号资料管理 API（简介、头像）"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.account import Account
from app.core.config import settings

router = APIRouter(prefix="/profile", tags=["账号资料"])


# ─── 请求/响应模型 ───

class SingleProfileUpdate(BaseModel):
    account_id: int
    biography: Optional[str] = None   # None = 不改简介


class BatchBioRequest(BaseModel):
    """批量修改简介（每账号可独立内容）"""
    updates: List[SingleProfileUpdate]


class ProfileJobStatus(BaseModel):
    account_id: int
    username: str
    status: str          # pending / success / failed
    message: str = ""


# ─── 批量修改简介 ───

@router.post("/batch-bio")
async def batch_update_bio(
    req: BatchBioRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    批量修改多个账号的 Instagram 简介。
    后台异步执行，立即返回任务 ID 列表。
    """
    results = []
    for item in req.updates:
        account = db.query(Account).filter(Account.id == item.account_id).first()
        if not account:
            results.append({"account_id": item.account_id, "status": "error", "message": "账号不存在"})
            continue
        if not account.ins_password_encrypted:
            results.append({
                "account_id": item.account_id,
                "username": account.username,
                "status": "error",
                "message": "未存储密码，请在账号编辑页填写密码",
            })
            continue
        if not item.biography:
            continue

        # 后台异步执行（逐个、带间隔）
        background_tasks.add_task(
            _do_update_bio,
            account.id, account.username,
            account.ins_password_encrypted,
            item.biography,
            account.proxy,
            account.ins_totp_secret_encrypted,
        )
        results.append({
            "account_id": item.account_id,
            "username": account.username,
            "status": "queued",
            "message": "已加入执行队列",
        })

    return {"queued": len([r for r in results if r.get("status") == "queued"]), "results": results}


async def _do_update_bio(account_id, username, pw_enc, bio, proxy, totp_enc):
    """后台执行简介修改"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        from app.services.profile_editor import update_biography
        await loop.run_in_executor(
            None,
            lambda: update_biography(account_id, username, pw_enc, bio, proxy, totp_enc)
        )
    except Exception as e:
        print(f"[Profile] 修改简介失败 {username}: {e}")


# ─── 上传头像文件（每账号单独上传）───

@router.post("/upload-avatar/{account_id}")
async def upload_avatar(
    account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传单个账号头像文件，保存到临时目录"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 检查文件类型
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    # 保存到上传目录
    avatar_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    save_path = os.path.join(avatar_dir, f"avatar_{account_id}.{ext}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    return {"account_id": account_id, "path": save_path, "size": len(content)}


# ─── 批量更换头像（使用已上传的头像文件）───

class BatchAvatarRequest(BaseModel):
    account_ids: List[int]  # 使用已通过 /upload-avatar/ 上传的头像


@router.post("/batch-avatar")
async def batch_update_avatar(
    req: BatchAvatarRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """批量更换头像（每账号独立头像，需先通过 /upload-avatar/ 上传）"""
    results = []
    avatar_dir = os.path.join(settings.UPLOAD_DIR, "avatars")

    for account_id in req.account_ids:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            results.append({"account_id": account_id, "status": "error", "message": "账号不存在"})
            continue

        # 找到该账号的头像文件
        avatar_path = None
        for ext in ("jpg", "jpeg", "png", "webp"):
            p = os.path.join(avatar_dir, f"avatar_{account_id}.{ext}")
            if os.path.exists(p):
                avatar_path = p
                break

        if not avatar_path:
            results.append({
                "account_id": account_id,
                "username": account.username,
                "status": "error",
                "message": "未找到头像文件，请先上传",
            })
            continue

        if not account.ins_password_encrypted:
            results.append({
                "account_id": account_id,
                "username": account.username,
                "status": "error",
                "message": "未存储密码",
            })
            continue

        background_tasks.add_task(
            _do_update_avatar,
            account.id, account.username,
            account.ins_password_encrypted,
            avatar_path, account.proxy,
            account.ins_totp_secret_encrypted,
        )
        results.append({"account_id": account_id, "username": account.username, "status": "queued"})

    return {"queued": len([r for r in results if r["status"] == "queued"]), "results": results}


async def _do_update_avatar(account_id, username, pw_enc, image_path, proxy, totp_enc):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        from app.services.profile_editor import update_avatar
        await loop.run_in_executor(
            None,
            lambda: update_avatar(account_id, username, pw_enc, image_path, proxy, totp_enc)
        )
    except Exception as e:
        print(f"[Profile] 更换头像失败 {username}: {e}")


# ─── 获取账号当前资料 ───

@router.get("/info/{account_id}")
def get_account_profile(account_id: int, db: Session = Depends(get_db)):
    """拉取账号的真实 Instagram 资料"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not account.ins_password_encrypted:
        raise HTTPException(status_code=400, detail="需要密码才能拉取资料")

    try:
        from app.services.profile_editor import get_profile_info
        return get_profile_info(
            account.id, account.username,
            account.ins_password_encrypted, account.proxy
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
