"""
定时任务模块数据模型

包含：
- ScheduledTask: 定时任务配置
- TaskExecutionLog: 任务执行日志

优化内容：
- 支持重试机制（可配置重试次数和间隔）
- 支持超时控制（任务级和CLI级超时）
- 支持执行锁（防止同一任务并发执行）
"""

from __future__ import annotations
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel
from sqlalchemy import DateTime, Text, Integer
from app.models.base import get_datetime_china


class TriggerType:
    """触发类型常量"""
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"


class TaskStatus:
    """任务状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


RETRY_BACKOFF_FACTOR = 2
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_INTERVAL = 60
DEFAULT_TIMEOUT = 300


class ScheduledTaskBase(SQLModel):
    """定时任务基础属性"""
    name: str = Field(max_length=100, description="任务名称")
    description: str | None = Field(default=None, max_length=500, description="任务描述")
    project_id: uuid.UUID | None = Field(default=None, foreign_key="projects.id", description="关联项目 ID")
    collection_id: str = Field(max_length=100, description="Apifox 测试集合 ID")
    collection_type: str = Field(default="test-suite", max_length=50, description="集合类型: test-suite/test-scenario")
    environment: str | None = Field(default=None, max_length=100, description="执行环境 ID")
    trigger_type: str = Field(max_length=20, description="触发类型: cron/interval/date")
    trigger_config: str = Field(sa_type=Text, description="触发配置 JSON")
    is_enabled: bool = Field(default=True, description="是否启用")
    notification_rule_id: uuid.UUID | None = Field(default=None, foreign_key="notification_rules.id", description="关联通知规则 ID")
    max_retries: int = Field(default=3, sa_type=Integer, description="最大重试次数，0表示不重试")
    retry_interval: int = Field(default=60, sa_type=Integer, description="重试间隔秒数")
    timeout_seconds: int = Field(default=300, sa_type=Integer, description="任务执行超时秒数")


class ScheduledTaskCreate(SQLModel):
    """创建定时任务"""
    name: str = Field(max_length=100)
    description: str | None = None
    project_id: uuid.UUID | None = None
    collection_id: str = Field(max_length=100)
    collection_type: str = Field(default="test-suite")
    environment: str | None = None
    trigger_type: str = Field(max_length=20)
    trigger_config: str
    is_enabled: bool = Field(default=True)
    notification_rule_id: uuid.UUID | None = None
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_interval: int = Field(default=60, description="重试间隔秒数")
    timeout_seconds: int = Field(default=300, description="任务执行超时秒数")


class ScheduledTaskUpdate(SQLModel):
    """更新定时任务"""
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    project_id: uuid.UUID | None = None
    collection_id: str | None = None
    collection_type: str | None = None
    environment: str | None = None
    trigger_type: str | None = None
    trigger_config: str | None = None
    is_enabled: bool | None = None
    notification_rule_id: uuid.UUID | None = None
    max_retries: int | None = None
    retry_interval: int | None = None
    timeout_seconds: int | None = None


class ScheduledTask(ScheduledTaskBase, table=True):
    """定时任务数据库模型"""
    __tablename__ = "scheduled_tasks"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    last_run_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="上次执行时间"
    )
    next_run_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="下次执行时间"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )


class ScheduledTaskPublic(ScheduledTaskBase):
    """定时任务公开数据"""
    id: uuid.UUID
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScheduledTasksPublic(SQLModel):
    """定时任务列表响应"""
    data: list[ScheduledTaskPublic]
    count: int


class TaskExecutionLogBase(SQLModel):
    """任务执行日志基础属性"""
    task_id: uuid.UUID = Field(foreign_key="scheduled_tasks.id", description="关联任务 ID")
    execution_id: uuid.UUID | None = Field(default=None, foreign_key="testexecution.id", description="关联执行 ID")
    status: str = Field(default="pending", max_length=20, description="执行状态: pending/running/completed/failed/timeout")
    error_message: str | None = Field(default=None, sa_type=Text, description="错误信息")
    retry_count: int = Field(default=0, description="当前重试次数")
    attempt_number: int = Field(default=1, description="当前尝试序号")


class TaskExecutionLog(TaskExecutionLogBase, table=True):
    """任务执行日志数据库模型"""
    __tablename__ = "task_execution_logs"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    started_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
        description="开始时间"
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="结束时间"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )


class TaskExecutionLogPublic(TaskExecutionLogBase):
    """任务执行日志公开数据"""
    id: uuid.UUID
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class TaskExecutionLogsPublic(SQLModel):
    """任务执行日志列表响应"""
    data: list[TaskExecutionLogPublic]
    count: int


class TriggerTaskRequest(SQLModel):
    """手动触发任务请求"""
    task_id: uuid.UUID


class EnableTaskResponse(SQLModel):
    """启用任务响应"""
    message: str
    next_run_at: datetime | None = None
