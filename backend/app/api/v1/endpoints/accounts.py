"""账号管理 API"""
import csv
import io
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account, Platform, AccountStatus, BrowserType
from app.schemas.account import AccountCreate, AccountUpdate, AccountOut, AccountImportRow
from app.core.encryption import encrypt, safe_decrypt
from app.api.deps import get_current_user, apply_owner_filter, verify_ownership

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
    request: Request,
    platform: Optional[Platform] = Query(None, description="按平台过滤"),
    status: Optional[AccountStatus] = Query(None, description="按状态过滤"),
    # 默认只返回启用中的账号；如需查看已停用账号，显式传 is_active=false 或不传该参数改用单独接口
    is_active: bool = Query(True, description="是否启用（默认只返回启用账号）"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取账号列表"""
    user = get_current_user(request)
    # 默认只查启用账号，避免软删除后仍显示在列表中
    q = db.query(Account).filter(Account.is_active == is_active)
    q = apply_owner_filter(q, Account, user)
    if platform:
        q = q.filter(Account.platform == platform)
    if status:
        q = q.filter(Account.status == status)
    rows = q.offset(skip).limit(limit).all()
    return [_account_to_out(row) for row in rows]


@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, request: Request, db: Session = Depends(get_db)):
    """创建单个账号"""
    user = get_current_user(request)
    owner_id = user["user_id"]

    # 唯一性检查：同一用户下同平台同用户名不能重复
    existing = db.query(Account).filter(
        Account.platform == payload.platform,
        Account.username == payload.username,
        Account.owner_id == owner_id,
    ).first()
    if existing:
        # 如果是已软删除账号，则视为「复活」而不是报重复
        if not existing.is_active:
            update_data = payload.model_dump(exclude={"ins_password", "ins_totp_secret", "ins_session_id"})
            for k, v in update_data.items():
                setattr(existing, k, v)
            # 加密存储密码（如果传了新的）
            if payload.ins_password:
                existing.ins_password_encrypted = encrypt(payload.ins_password)
            if payload.ins_totp_secret:
                existing.ins_totp_secret_encrypted = encrypt(payload.ins_totp_secret)
            if payload.ins_session_id:
                existing.ins_session_id_encrypted = encrypt(payload.ins_session_id)
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

    data = payload.model_dump(exclude={"ins_password", "ins_totp_secret", "ins_session_id"})
    account = Account(**data, owner_id=owner_id)

    # 加密存储密码
    if payload.ins_password:
        account.ins_password_encrypted = encrypt(payload.ins_password)
    if payload.ins_totp_secret:
        account.ins_totp_secret_encrypted = encrypt(payload.ins_totp_secret)
    if payload.ins_session_id:
        account.ins_session_id_encrypted = encrypt(payload.ins_session_id)

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
    data.has_session_id = bool(account.ins_session_id_encrypted)
    data.has_yt_token = bool(account.yt_oauth_token)
    return data


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    """获取单个账号"""
    user = get_current_user(request)
    account = verify_ownership(db, Account, account_id, user)
    return _account_to_out(account)


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, request: Request, db: Session = Depends(get_db)):
    """更新账号信息"""
    user = get_current_user(request)
    account = verify_ownership(db, Account, account_id, user)

    update_data = payload.model_dump(exclude_unset=True)
    new_password = update_data.pop("ins_password", None)
    new_totp = update_data.pop("ins_totp_secret", None)
    new_session_id = update_data.pop("ins_session_id", None)

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

    # 显式传入密码/TOTP/SessionID 时，更新加密字段
    if new_password is not None:
        account.ins_password_encrypted = encrypt(new_password) if new_password else None
    if new_totp is not None:
        account.ins_totp_secret_encrypted = encrypt(new_totp) if new_totp else None
    if new_session_id is not None:
        account.ins_session_id_encrypted = encrypt(new_session_id) if new_session_id else None

    db.commit()
    db.refresh(account)
    return _account_to_out(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    """删除账号（软删除：仅禁用，不物理删除）

    说明：
    - 之前这里直接 db.delete(account)，当账号下存在发布任务等外键关联时，容易触发数据库外键约束错误
    - 现在改为「软删除」：将 is_active 置为 False，避免破坏既有任务/日志数据
    """
    user = get_current_user(request)
    account = verify_ownership(db, Account, account_id, user)
    # 如果已经处于禁用状态，直接返回 204，保持幂等性
    if not account.is_active:
        return

    # 软删除：仅标记为未启用，避免级联删除导致的外键错误
    account.is_active = False
    db.commit()


@router.post("/import/csv", response_model=dict)
async def import_accounts_csv(
    request: Request,
    file: UploadFile = File(..., description="CSV 文件，列：name,username,platform,proxy,adspower_profile_id,notes"),
    db: Session = Depends(get_db),
):
    """批量导入账号（CSV）"""
    user = get_current_user(request)
    owner_id = user["user_id"]

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
                Account.owner_id == owner_id,
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
                    existing.owner_id = owner_id
                    created += 1
                    continue
                # 启用中的重复账号，跳过
                skipped += 1
                continue
            db.add(Account(**data, owner_id=owner_id))
            created += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


@router.post("/{account_id}/check-status", response_model=AccountOut)
def check_account_status(account_id: int, request: Request, db: Session = Depends(get_db)):
    """手动触发账号登录检测

    - instagrapi 账号：实际尝试登录，返回真实状态
    - 指纹浏览器账号：无法自动检测，返回 422
    """
    user = get_current_user(request)
    account = verify_ownership(db, Account, account_id, user)

    account.last_checked_at = datetime.utcnow()

    # 指纹浏览器账号无法在服务器端自动检测
    if account.browser_type != BrowserType.NONE:
        db.commit()
        raise HTTPException(
            status_code=422,
            detail="指纹浏览器账号无法自动检测，请通过浏览器手动确认登录状态"
        )

    # instagrapi 账号：session_id 或密码至少有一个才能检测
    session_id = safe_decrypt(account.ins_session_id_encrypted)
    password = safe_decrypt(account.ins_password_encrypted)

    if not session_id and not password:
        account.status = AccountStatus.UNKNOWN
        db.commit()
        db.refresh(account)
        return _account_to_out(account)

    totp_secret = safe_decrypt(account.ins_totp_secret_encrypted)

    try:
        from instagrapi import Client

        cl = Client()

        def _no_challenge(username, choice):
            raise RuntimeError("需要邮件/短信验证码，请先通过手机 App 完成验证后再检测")
        cl.challenge_code_handler = _no_challenge

        if account.proxy:
            cl.set_proxy(account.proxy)

        # 优先用 session_id（免安全验证）
        if session_id:
            cl.login_by_sessionid(session_id)
        else:
            totp_code = ""
            if totp_secret:
                import pyotp
                totp_code = pyotp.TOTP(totp_secret).now()
            cl.login(account.username, password, verification_code=totp_code)

        account.status = AccountStatus.ACTIVE

    except Exception:
        account.status = AccountStatus.SUSPENDED

    db.commit()
    db.refresh(account)
    return _account_to_out(account)
