"""账号相关 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.account import Platform, AccountStatus, BrowserType


class AccountBase(BaseModel):
    name: str = Field(..., max_length=100)
    username: str = Field(..., max_length=100)
    platform: Platform
    group_name: Optional[str] = Field(None, max_length=100, description="账号分组")
    proxy: Optional[str] = None
    browser_type: BrowserType = BrowserType.ADSPOWER
    browser_profile_id: Optional[str] = None
    yt_channel_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class AccountCreate(AccountBase):
    ins_password: Optional[str] = Field(None, description="INS 密码（写入后加密存储，接口不返回）")
    ins_totp_secret: Optional[str] = Field(None, description="INS TOTP 2FA 密钥")


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    group_name: Optional[str] = None
    proxy: Optional[str] = None
    browser_type: Optional[BrowserType] = None
    browser_profile_id: Optional[str] = None
    yt_channel_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[AccountStatus] = None
    ins_password: Optional[str] = None
    ins_totp_secret: Optional[str] = None


class AccountOut(AccountBase):
    id: int
    status: AccountStatus
    has_password: bool = False    # 是否已存储密码（不返回明文）
    has_totp: bool = False
    has_yt_token: bool = False
    created_at: datetime
    updated_at: datetime
    last_checked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AccountImportRow(BaseModel):
    """CSV 批量导入单行数据格式"""
    name: str
    username: str
    platform: Platform
    group_name: Optional[str] = None
    proxy: Optional[str] = None
    browser_type: Optional[str] = "adspower"
    browser_profile_id: Optional[str] = None
    ins_password: Optional[str] = None  # Instagram密码（将自动加密存储）
    ins_totp_secret: Optional[str] = None  # Instagram 2FA TOTP密钥
    notes: Optional[str] = None
