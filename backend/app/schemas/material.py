"""素材相关 Pydantic Schema"""
import os
import json
from pydantic import BaseModel, Field, computed_field, field_validator
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
    tags: Optional[List[str]] = Field(default_factory=list, description="素材标签列表")
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

    @computed_field
    @property
    def file_url(self) -> Optional[str]:
        """返回文件的URL路径（用于前端访问）"""
        if not self.file_path:
            return None
        # 从绝对路径提取文件名，返回/uploads/文件名
        filename = os.path.basename(self.file_path)
        return f"/uploads/{filename}"

    @computed_field
    @property
    def thumbnail_url(self) -> Optional[str]:
        """返回缩略图的URL路径"""
        if not self.thumbnail_path:
            return None
        filename = os.path.basename(self.thumbnail_path)
        return f"/uploads/{filename}"

    @classmethod
    def from_orm_with_accounts(cls, obj):
        data = cls.model_validate(obj)
        data.target_account_ids = [a.id for a in obj.target_accounts]
        # 解析tags JSON字符串为列表
        if hasattr(obj, 'tags') and obj.tags:
            try:
                data.tags = json.loads(obj.tags) if isinstance(obj.tags, str) else obj.tags
            except (json.JSONDecodeError, TypeError):
                data.tags = []
        else:
            data.tags = []
        return data
