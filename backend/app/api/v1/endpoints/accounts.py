"""账号管理 API"""
import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account, Platform, AccountStatus
from app.schemas.account import AccountCreate, AccountUpdate, AccountOut, AccountImportRow

router = APIRouter(prefix="/accounts", tags=["账号管理"])


@router.get("/", response_model=List[AccountOut])
def list_accounts(
    platform: Optional[Platform] = Query(None, description="按平台过滤"),
    status: Optional[AccountStatus] = Query(None, description="按状态过滤"),
    is_active: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取账号列表"""
    q = db.query(Account)
    if platform:
        q = q.filter(Account.platform == platform)
    if status:
        q = q.filter(Account.status == status)
    if is_active is not None:
        q = q.filter(Account.is_active == is_active)
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    """创建单个账号"""
    from app.core.encryption import encrypt

    existing = db.query(Account).filter(
        Account.platform == payload.platform,
        Account.username == payload.username,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"账号 {payload.username} 在 {payload.platform} 已存在")

    data = payload.model_dump(exclude={"ins_password", "ins_totp_secret"})
    account = Account(**data)

    # 加密存储密码
    if payload.ins_password:
        account.ins_password_encrypted = encrypt(payload.ins_password)
    if payload.ins_totp_secret:
        account.ins_totp_secret_encrypted = encrypt(payload.ins_totp_secret)

    # 向后兼容：同步 browser_profile_id 到 adspower_profile_id
    if payload.browser_profile_id:
        account.adspower_profile_id = payload.browser_profile_id

    db.add(account)
    db.commit()
    db.refresh(account)
    return _account_to_out(account)


def _account_to_out(account: Account) -> AccountOut:
    """转换账号模型到输出 Schema，补充 has_* 字段"""
    data = AccountOut.model_validate(account)
    data.has_password = bool(account.ins_password_encrypted)
    data.has_totp = bool(account.ins_totp_secret_encrypted)
    data.has_yt_token = bool(account.yt_oauth_token)
    return data


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    """获取单个账号"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    """更新账号信息"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(account, k, v)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除账号"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    db.delete(account)
    db.commit()


@router.post("/import/csv", response_model=dict)
async def import_accounts_csv(
    file: UploadFile = File(..., description="CSV 文件，列：name,username,platform,proxy,adspower_profile_id,notes"),
    db: Session = Depends(get_db),
):
    """批量导入账号（CSV）"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="请上传 .csv 文件")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # 处理带 BOM 的 Excel CSV
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    created, skipped, errors = 0, 0, []

    for i, row in enumerate(reader, start=2):  # 从第 2 行开始（第 1 行是表头）
        try:
            item = AccountImportRow(**{k.strip(): v.strip() for k, v in row.items() if v})
            existing = db.query(Account).filter(
                Account.platform == item.platform,
                Account.username == item.username,
            ).first()
            if existing:
                skipped += 1
                continue
            db.add(Account(**item.model_dump()))
            created += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


@router.post("/{account_id}/check-status", response_model=AccountOut)
def check_account_status(account_id: int, db: Session = Depends(get_db)):
    """手动触发账号健康检测（异步任务）"""
    from app.tasks.health_check import check_account_health
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 发送 Celery 任务
    check_account_health.delay(account_id)
    return account
