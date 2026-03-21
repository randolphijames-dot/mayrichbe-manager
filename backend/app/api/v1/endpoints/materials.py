"""素材管理 API"""
import json
import logging
import mimetypes
import os
import shutil
import subprocess
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.models.account import Account
from app.models.material import Material, MaterialType, MaterialStatus
from app.schemas.material import MaterialCreate, MaterialUpdate, MaterialOut
from app.api.deps import get_current_user, apply_owner_filter, verify_ownership, verify_batch_ownership

router = APIRouter(prefix="/materials", tags=["素材管理"])
logger = logging.getLogger(__name__)

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _resolve_mime_type(file: UploadFile) -> str:
    """优先信任明确的 MIME；octet-stream 时回退到文件后缀。"""
    guessed = mimetypes.guess_type(file.filename or "")[0]
    uploaded = (file.content_type or "").strip().lower()
    if uploaded and uploaded != "application/octet-stream":
        return uploaded
    return guessed or uploaded or "application/octet-stream"


def _resolve_ffmpeg_executable() -> Optional[str]:
    """查找 ffmpeg；如果系统没装，则回退到 imageio-ffmpeg 自带二进制。"""
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        return ffmpeg_bin
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - 仅在运行环境缺依赖时触发
        logger.warning("[Materials] 未找到可用 ffmpeg: %s", exc)
        return None


@router.get("/", response_model=List[MaterialOut])
def list_materials(
    request: Request,
    material_type: Optional[MaterialType] = None,
    status: Optional[MaterialStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取素材列表"""
    user = get_current_user(request)
    q = db.query(Material)
    q = apply_owner_filter(q, Material, user)
    if material_type:
        q = q.filter(Material.material_type == material_type)
    if status:
        q = q.filter(Material.status == status)
    materials = q.order_by(Material.created_at.desc()).offset(skip).limit(limit).all()
    return [MaterialOut.from_orm_with_accounts(m) for m in materials]


@router.post("/upload", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
async def upload_material(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    yt_title: Optional[str] = Form(None),
    yt_tags: Optional[str] = Form(None),
    yt_privacy: str = Form("public"),
    material_type: MaterialType = Form(...),
    folder_tag: Optional[str] = Form(None, description="文件夹标签，如 2026-03-10"),
    target_account_ids: Optional[str] = Form(None, description="账号 ID 列表，逗号分隔"),
    db: Session = Depends(get_db),
):
    """上传素材文件"""
    user = get_current_user(request)
    owner_id = user["user_id"]

    # 文件大小检查
    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"文件超过 {settings.MAX_FILE_SIZE_MB}MB 限制")

    # MIME 类型检查
    mime_type = _resolve_mime_type(file)
    allowed = ALLOWED_VIDEO_TYPES | ALLOWED_IMAGE_TYPES
    if mime_type not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {mime_type}")

    # 自动修正素材类型（根据 MIME 判断，不信任前端传入的类型）
    if mime_type in ALLOWED_IMAGE_TYPES:
        material_type = MaterialType.IMAGE
    elif mime_type in ALLOWED_VIDEO_TYPES:
        material_type = MaterialType.VIDEO
    else:
        raise HTTPException(status_code=400, detail=f"无法识别文件类型: {mime_type}")

    # 保存文件
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    safe_filename = f"{os.urandom(8).hex()}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # 生成缩略图
    thumbnail_path = None
    if mime_type in ALLOWED_IMAGE_TYPES:
        # 图片直接使用原文件作为缩略图
        thumbnail_path = file_path
    elif mime_type in ALLOWED_VIDEO_TYPES:
        # 视频提取第一帧作为缩略图
        try:
            thumb_filename = f"thumb_{safe_filename}.jpg"
            thumb_path = os.path.join(upload_dir, thumb_filename)
            ffmpeg_bin = _resolve_ffmpeg_executable()
            if not ffmpeg_bin:
                raise RuntimeError("ffmpeg 不可用，无法生成视频缩略图")
            subprocess.run([
                ffmpeg_bin, '-i', file_path, '-vframes', '1',
                '-vf', 'scale=480:-1', '-q:v', '2', thumb_path
            ], check=True, capture_output=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            thumbnail_path = thumb_path
        except Exception as e:
            # 缩略图生成失败不影响上传，只记录警告
            logger.warning("[Materials] 缩略图生成失败: %s", e)

    # 解析账号 ID 列表
    account_ids = []
    if target_account_ids:
        try:
            account_ids = [int(x.strip()) for x in target_account_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="target_account_ids 格式错误，请用逗号分隔整数")

    # 验证账号存在 + 所有权
    accounts = []
    if account_ids:
        accounts = verify_batch_ownership(db, Account, account_ids, user)

    material = Material(
        title=title or file.filename,
        material_type=material_type,
        status=MaterialStatus.READY,
        file_path=file_path,
        file_size=len(content),
        mime_type=mime_type,
        thumbnail_path=thumbnail_path,
        caption=caption,
        yt_title=yt_title,
        yt_tags=yt_tags,
        yt_privacy=yt_privacy,
        folder_tag=folder_tag,
        target_accounts=accounts,
        owner_id=owner_id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return MaterialOut.from_orm_with_accounts(material)


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(material_id: int, request: Request, db: Session = Depends(get_db)):
    """获取单个素材"""
    user = get_current_user(request)
    material = verify_ownership(db, Material, material_id, user)
    return MaterialOut.from_orm_with_accounts(material)


@router.patch("/{material_id}", response_model=MaterialOut)
def update_material(material_id: int, payload: MaterialUpdate, request: Request, db: Session = Depends(get_db)):
    """更新素材信息"""
    user = get_current_user(request)
    material = verify_ownership(db, Material, material_id, user)

    update_data = payload.model_dump(exclude_unset=True)
    account_ids = update_data.pop("target_account_ids", None)

    # 处理tags：将列表转换为JSON字符串
    if "tags" in update_data:
        tags_list = update_data.pop("tags")
        if tags_list is not None:
            material.tags = json.dumps(tags_list, ensure_ascii=False) if tags_list else None

    for k, v in update_data.items():
        setattr(material, k, v)

    if account_ids is not None:
        # 验证关联账号的所有权
        accounts = verify_batch_ownership(db, Account, account_ids, user)
        material.target_accounts = accounts

    db.commit()
    db.refresh(material)
    return MaterialOut.from_orm_with_accounts(material)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: int, request: Request, db: Session = Depends(get_db)):
    """删除素材（同时删除本地文件）"""
    from app.models.task import PublishTask

    user = get_current_user(request)
    material = verify_ownership(db, Material, material_id, user)

    # 检查是否有发布任务引用此素材
    linked_tasks = db.query(PublishTask).filter(PublishTask.material_id == material_id).count()
    if linked_tasks > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除：此素材被 {linked_tasks} 个发布任务引用。请先删除相关任务或取消任务关联。"
        )

    # 删除物理文件（原文件）
    if material.file_path and os.path.exists(material.file_path):
        try:
            os.remove(material.file_path)
        except OSError as e:
            logger.warning(f"[Materials] 删除文件失败 {material.file_path}: {e}")

    # 删除缩略图文件（如果与原文件不同）
    if material.thumbnail_path and material.thumbnail_path != material.file_path:
        if os.path.exists(material.thumbnail_path):
            try:
                os.remove(material.thumbnail_path)
            except OSError as e:
                logger.warning(f"[Materials] 删除缩略图失败 {material.thumbnail_path}: {e}")

    db.delete(material)
    db.commit()
