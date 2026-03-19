"""账号管理 API"""
import csv
import io
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account, Platform, AccountStatus, BrowserType
from app.schemas.account import AccountCreate, AccountUpdate, AccountOut, AccountImportRow
from app.core.encryption import encrypt

router = APIRouter(prefix="/accounts", tags=["账号管理"])


def _validate_browser_config_for_bitbrowser(
    browser_type: BrowserType | None,
    browser_profile_id: str | None,
) -> None:
    """校验比特浏览器配置是否有效（轻量版）。

    - 仅在 browser_type 为 BITBROWSER 时生效
    - 要求必须提供 browser_profile_id
    - 出于兼容不同版本 BitBrowser，本函数**不再强制调用本地 API 做连通性检查**，
      避免由于接口路径差异导致账号无法保存。
    实际连通性由发布/调试流程中的 BitBrowser 客户端负责检测，并给出更具体的错误信息。
    """
    if browser_type not in (BrowserType.BITBROWSER, "bitbrowser"):
        return

    if not browser_profile_id:
        raise HTTPException(
            status_code=400,
            detail="已选择比特浏览器，但未填写 Profile ID，请先在 BitBrowser 中创建配置并填写其 ID。",
        )


@router.get("/", response_model=List[AccountOut])
def list_accounts(
    platform: Optional[Platform] = Query(None, description="按平台过滤"),
    status: Optional[AccountStatus] = Query(None, description="按状态过滤"),
    # 默认只返回启用中的账号；如需查看已停用账号，显式传 is_active=false 或不传该参数改用单独接口
    is_active: bool = Query(True, description="是否启用（默认只返回启用账号）"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取账号列表"""
    # 默认只查启用账号，避免软删除后仍显示在列表中
    q = db.query(Account).filter(Account.is_active == is_active)
    if platform:
        q = q.filter(Account.platform == platform)
    if status:
        q = q.filter(Account.status == status)
    rows = q.offset(skip).limit(limit).all()
    return [_account_to_out(row) for row in rows]


@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    """创建单个账号"""
    existing = db.query(Account).filter(
        Account.platform == payload.platform,
        Account.username == payload.username,
    ).first()
    if existing:
        # 如果是已软删除账号，则视为「复活」而不是报重复
        if not existing.is_active:
            update_data = payload.model_dump(exclude={"ins_password", "ins_totp_secret"})
            for k, v in update_data.items():
                setattr(existing, k, v)
            # 加密存储密码（如果传了新的）
            if payload.ins_password:
                existing.ins_password_encrypted = encrypt(payload.ins_password)
            if payload.ins_totp_secret:
                existing.ins_totp_secret_encrypted = encrypt(payload.ins_totp_secret)
            # 向后兼容：同步 browser_profile_id 到 adspower_profile_id
            if payload.browser_profile_id:
                existing.adspower_profile_id = payload.browser_profile_id
            # 重新启用账号
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return _account_to_out(existing)

        # 已存在且是启用状态，仍然视为重复
        raise HTTPException(status_code=409, detail=f"账号 {payload.username} 在 {payload.platform} 已存在")

    # 在写入数据库前校验指纹浏览器配置
    _validate_browser_config_for_bitbrowser(
        browser_type=payload.browser_type,
        browser_profile_id=payload.browser_profile_id,
    )

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
    return _account_to_out(account)


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    """更新账号信息"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    update_data = payload.model_dump(exclude_unset=True)
    new_password = update_data.pop("ins_password", None)
    new_totp = update_data.pop("ins_totp_secret", None)

    # 如果前端修改了浏览器类型或 Profile ID，需要重新校验
    new_browser_type = update_data.get("browser_type", account.browser_type)
    new_profile_id = update_data.get("browser_profile_id", account.browser_profile_id)
    _validate_browser_config_for_bitbrowser(
        browser_type=new_browser_type,
        browser_profile_id=new_profile_id,
    )
    for k, v in update_data.items():
        setattr(account, k, v)

    # 兼容历史字段
    if "browser_profile_id" in update_data and update_data.get("browser_profile_id"):
        account.adspower_profile_id = update_data["browser_profile_id"]

    # 显式传入密码/TOTP 时，更新加密字段
    if new_password is not None:
        account.ins_password_encrypted = encrypt(new_password) if new_password else None
    if new_totp is not None:
        account.ins_totp_secret_encrypted = encrypt(new_totp) if new_totp else None

    db.commit()
    db.refresh(account)
    return _account_to_out(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除账号（软删除：仅禁用，不物理删除）

    说明：
    - 之前这里直接 db.delete(account)，当账号下存在发布任务等外键关联时，容易触发数据库外键约束错误
    - 现在改为「软删除」：将 is_active 置为 False，避免破坏既有任务/日志数据
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    # 如果已经处于禁用状态，直接返回 204，保持幂等性
    if not account.is_active:
        return

    # 软删除：仅标记为未启用，避免级联删除导致的外键错误
    account.is_active = False
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

            # 准备数据（处理密码加密）
            data = item.model_dump()
            if data.get("ins_password"):
                data["ins_password_encrypted"] = encrypt(data.pop("ins_password"))
            if data.get("ins_totp_secret"):
                data["ins_totp_secret_encrypted"] = encrypt(data.pop("ins_totp_secret"))

            if existing:
                # 如果是已软删除账号，视为复活并更新字段
                if not existing.is_active:
                    for k, v in data.items():
                        setattr(existing, k, v)
                    existing.is_active = True
                    created += 1
                    continue
                # 启用中的重复账号，跳过
                skipped += 1
                continue
            db.add(Account(**data))
            created += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


@router.post("/{account_id}/check-status", response_model=AccountOut)
def check_account_status(account_id: int, db: Session = Depends(get_db)):
    """手动触发账号健康检测（异步任务）

    最小可用版本实现：
    - 直接将账号状态标记为 ACTIVE
    - 更新 last_checked_at 为当前时间
    - 不做真实外部检测，仅作为「已检测」标记
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 最小可用版：直接标记为已检测且状态正常
    account.status = AccountStatus.ACTIVE
    account.last_checked_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    return _account_to_out(account)
