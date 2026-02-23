# 兼容层：从新的模块重新导出所有模型
# 注意：新代码建议直接从 app.models.xxx 导入

# 基础
from app.models.base import CHINA_TZ, get_datetime_china

# 用户模型
from app.models.user import (
    UserBase,
    UserCreate,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
    UpdatePassword,
    User,
    UserPublic,
    UsersPublic,
)

# 项目模型
from app.models.item import (
    ItemBase,
    ItemCreate,
    ItemUpdate,
    Item,
    ItemPublic,
    ItemsPublic,
)

# 测试执行模型
from app.models.execution import (
    ExecutionStatus,
    TestExecutionBase,
    TestExecutionCreate,
    TestExecutionUpdate,
    TestExecution,
    TestExecutionPublic,
    TestExecutionsPublic,
    ExecutionStats,
)

# 定时任务模型
from app.models.scheduled_task import (
    TriggerType,
    TaskStatus,
    ScheduledTaskBase,
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTask,
    ScheduledTaskPublic,
    ScheduledTasksPublic,
    TaskExecutionLogBase,
    TaskExecutionLog,
    TaskExecutionLogPublic,
    TaskExecutionLogsPublic,
    TriggerTaskRequest,
)

# 缺陷管理模型
from app.models.defect import (
    DefectSeverity,
    DefectPriority,
    DefectStatus,
    DefectType,
    Defect,
    DefectCreate,
    DefectUpdate,
    DefectPublic,
    DefectsPublic,
    DefectStats,
)

# 其他模型（保持原样）
from sqlmodel import SQLModel
from pydantic import BaseModel
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


class Message(BaseModel):
    message: str


class NewPassword(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


__all__ = [
    # 基础
    "CHINA_TZ",
    "get_datetime_china",
    # 用户
    "UserBase",
    "UserCreate",
    "UserRegister",
    "UserUpdate",
    "UserUpdateMe",
    "UpdatePassword",
    "User",
    "UserPublic",
    "UsersPublic",
    # 项目
    "ItemBase",
    "ItemCreate",
    "ItemUpdate",
    "Item",
    "ItemPublic",
    "ItemsPublic",
    # 测试执行
    "ExecutionStatus",
    "TestExecutionBase",
    "TestExecutionCreate",
    "TestExecutionUpdate",
    "TestExecution",
    "TestExecutionPublic",
    "TestExecutionsPublic",
    "ExecutionStats",
    # 定时任务
    "TriggerType",
    "TaskStatus",
    "ScheduledTaskBase",
    "ScheduledTaskCreate",
    "ScheduledTaskUpdate",
    "ScheduledTask",
    "ScheduledTaskPublic",
    "ScheduledTasksPublic",
    "TaskExecutionLogBase",
    "TaskExecutionLog",
    "TaskExecutionLogPublic",
    "TaskExecutionLogsPublic",
    "TriggerTaskRequest",
    # 缺陷管理
    "DefectSeverity",
    "DefectPriority",
    "DefectStatus",
    "DefectType",
    "Defect",
    "DefectCreate",
    "DefectUpdate",
    "DefectPublic",
    "DefectsPublic",
    "DefectStats",
    # 其他
    "Token",
    "TokenPayload",
    "Message",
    "NewPassword",
    "SQLModel",
]