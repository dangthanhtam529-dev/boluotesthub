# 项目相关模型
from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel
from app.models.base import get_datetime_china

if TYPE_CHECKING:
    from app.models.user import User


# ============ 基础属性 ============
class ItemBase(SQLModel):
    """项目基础属性"""
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# ============ 创建/更新 ============
class ItemCreate(ItemBase):
    """创建项目时接收的数据"""
    pass


class ItemUpdate(ItemBase):
    """更新项目时接收的数据（所有字段可选）"""
    title: str | None = Field(default=None, min_length=1, max_length=255)


# ============ 数据库模型 ============
class Item(ItemBase, table=True):
    """项目数据库模型"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )


# ============ 响应模型 ============
class ItemPublic(ItemBase):
    """返回给前端的项目数据"""
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    """项目列表响应"""
    data: list[ItemPublic]
    count: int
