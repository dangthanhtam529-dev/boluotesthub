from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_china


class AuditStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class AuditLogBase(SQLModel):
    request_id: str | None = Field(default=None, index=True, max_length=64)
    actor_user_id: uuid.UUID | None = Field(default=None, index=True)
    actor_email: str | None = Field(default=None, max_length=255)
    actor_ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, sa_type=Text)

    action: str = Field(index=True, max_length=64)
    resource_type: str = Field(index=True, max_length=64)
    resource_id: str | None = Field(default=None, index=True, max_length=128)
    resource_name: str | None = Field(default=None, max_length=255)

    before: dict[str, Any] | None = Field(default=None, sa_type=JSON)
    after: dict[str, Any] | None = Field(default=None, sa_type=JSON)
    diff_summary: str | None = Field(default=None, max_length=1000)

    status: str = Field(index=True, max_length=16)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, sa_type=Text)
    duration_ms: int | None = Field(default=None)


class AuditLog(AuditLogBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
        index=True,
    )


class AuditLogPublic(AuditLogBase):
    id: uuid.UUID
    created_at: datetime | None = None


class AuditLogsPublic(SQLModel):
    data: list[AuditLogPublic]
    count: int

