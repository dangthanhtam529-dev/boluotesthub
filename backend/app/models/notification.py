"""
通知模块数据模型

包含：
- NotificationChannel: 通知渠道配置（钉钉/企微/邮件）
- NotificationRule: 通知规则配置
- NotificationLog: 通知发送记录
"""

from __future__ import annotations
import enum
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel
from sqlalchemy import DateTime, Text
from app.models.base import get_datetime_china


class ChannelType(str, enum.Enum):
    """通知渠道类型"""
    DINGTALK = "dingtalk"
    WEWORK = "wework"
    EMAIL = "email"


class TriggerType(str, enum.Enum):
    """通知触发类型"""
    EXECUTION_DONE = "execution_done"
    EXECUTION_FAILED = "execution_failed"
    THRESHOLD_ALERT = "threshold_alert"
    DAILY_REPORT = "daily_report"
    WEEKLY_REPORT = "weekly_report"


class NotificationStatus(str, enum.Enum):
    """通知发送状态"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationChannelBase(SQLModel):
    """通知渠道基础属性"""
    name: str = Field(max_length=100, description="渠道名称")
    channel_type: str = Field(max_length=20, description="渠道类型: dingtalk/wework/email")
    config: str = Field(sa_type=Text, description="渠道配置 JSON")
    description: str | None = Field(default=None, max_length=500, description="渠道描述")
    is_enabled: bool = Field(default=True, description="是否启用")


class NotificationChannelCreate(NotificationChannelBase):
    """创建通知渠道"""
    pass


class NotificationChannelUpdate(SQLModel):
    """更新通知渠道"""
    name: str | None = Field(default=None, max_length=100)
    config: str | None = Field(default=None)
    description: str | None = Field(default=None)
    is_enabled: bool | None = Field(default=None)


class NotificationChannel(NotificationChannelBase, table=True):
    """通知渠道数据库模型"""
    __tablename__ = "notification_channels"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )


class NotificationChannelPublic(SQLModel):
    """通知渠道公开数据（不含敏感配置）"""
    id: uuid.UUID
    name: str
    channel_type: str
    description: str | None = None
    is_enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NotificationChannelsPublic(SQLModel):
    """通知渠道列表响应"""
    data: list[NotificationChannelPublic]
    count: int


class NotificationRuleBase(SQLModel):
    """通知规则基础属性"""
    name: str = Field(max_length=100, description="规则名称")
    trigger_type: str = Field(max_length=50, description="触发类型")
    trigger_config: str | None = Field(default=None, sa_type=Text, description="触发条件配置 JSON")
    channel_ids: str = Field(sa_type=Text, description="通知渠道 ID 列表 JSON")
    template: str | None = Field(default=None, sa_type=Text, description="消息模板")
    project_id: uuid.UUID | None = Field(default=None, foreign_key="projects.id", description="关联项目 ID")
    is_enabled: bool = Field(default=True, description="是否启用")
    description: str | None = Field(default=None, max_length=500, description="规则描述")


class NotificationRuleCreate(NotificationRuleBase):
    """创建通知规则"""
    pass


class NotificationRuleUpdate(SQLModel):
    """更新通知规则"""
    name: str | None = Field(default=None, max_length=100)
    trigger_type: str | None = Field(default=None, max_length=50)
    trigger_config: str | None = Field(default=None)
    channel_ids: str | None = Field(default=None)
    template: str | None = Field(default=None)
    project_id: uuid.UUID | None = Field(default=None)
    is_enabled: bool | None = Field(default=None)
    description: str | None = Field(default=None)


class NotificationRule(NotificationRuleBase, table=True):
    """通知规则数据库模型"""
    __tablename__ = "notification_rules"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )


class NotificationRulePublic(NotificationRuleBase):
    """通知规则公开数据"""
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NotificationRulesPublic(SQLModel):
    """通知规则列表响应"""
    data: list[NotificationRulePublic]
    count: int


class NotificationLogBase(SQLModel):
    """通知日志基础属性"""
    rule_id: uuid.UUID | None = Field(default=None, foreign_key="notification_rules.id", description="关联规则 ID")
    channel_id: uuid.UUID | None = Field(default=None, foreign_key="notification_channels.id", description="关联渠道 ID")
    channel_type: str = Field(max_length=20, description="渠道类型")
    channel_name: str = Field(max_length=100, description="渠道名称")
    title: str = Field(max_length=200, description="通知标题")
    content: str = Field(sa_type=Text, description="通知内容")
    status: str = Field(default="pending", description="发送状态: pending/sent/failed")
    error_message: str | None = Field(default=None, sa_type=Text, description="错误信息")
    execution_id: uuid.UUID | None = Field(default=None, foreign_key="testexecution.id", description="关联执行 ID")


class NotificationLog(NotificationLogBase, table=True):
    """通知日志数据库模型"""
    __tablename__ = "notification_logs"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    sent_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="发送时间"
    )


class NotificationLogPublic(NotificationLogBase):
    """通知日志公开数据"""
    id: uuid.UUID
    created_at: datetime | None = None
    sent_at: datetime | None = None


class NotificationLogsPublic(SQLModel):
    """通知日志列表响应"""
    data: list[NotificationLogPublic]
    count: int


class TestNotificationRequest(SQLModel):
    """测试通知请求"""
    channel_id: uuid.UUID = Field(description="渠道 ID")
    test_message: str | None = Field(default=None, max_length=500, description="测试消息内容")


class TestNotificationResponse(SQLModel):
    """测试通知响应"""
    success: bool
    message: str
    error: str | None = None
