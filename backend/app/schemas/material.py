"""素材相关 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.material import MaterialType, MaterialStatus


class MaterialBase(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    material_type: MaterialType
    caption: Optional[str] = None
    yt_title: Optional[str] = Field(None, max_length=200)
    yt_tags: Optional[str] = None       # JSON 数组字符串
    yt_category_id: Optional[str] = None
    yt_privacy: str = "public"
    folder_tag: Optional[str] = None
    notes: Optional[str] = None


class MaterialCreate(MaterialBase):
    target_account_ids: Optional[List[int]] = Field(default_factory=list, description="目标账号 ID 列表")


class MaterialUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    yt_title: Optional[str] = None
    yt_tags: Optional[str] = None
    yt_category_id: Optional[str] = None
    yt_privacy: Optional[str] = None
    notes: Optional[str] = None
    target_account_ids: Optional[List[int]] = None


class MaterialOut(MaterialBase):
    id: int
    status: MaterialStatus
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    thumbnail_path: Optional[str] = None
    duration_seconds: Optional[int] = None
    target_account_ids: List[int] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_accounts(cls, obj):
        data = cls.model_validate(obj)
        data.target_account_ids = [a.id for a in obj.target_accounts]
        return data
