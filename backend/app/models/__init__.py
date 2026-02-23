# 模型模块 - 按功能拆分的数据库模型
from sqlmodel import SQLModel

from app.models.user import User, UserBase, UserCreate, UserRegister, UserUpdate, UserUpdateMe, UpdatePassword, UserPublic, UsersPublic
from app.models.item import Item, ItemBase, ItemCreate, ItemUpdate, ItemPublic, ItemsPublic
from app.models.execution import TestExecution, TestExecutionCreate, TestExecutionUpdate, TestExecutionPublic, TestExecutionsPublic
from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectPublic, ProjectsPublic, Collection, CollectionCreate, CollectionUpdate, CollectionPublic, CollectionsPublic, ProjectStats
from app.models.audit_log import AuditLog, AuditLogPublic, AuditLogsPublic
from app.models.notification import (
    NotificationChannel, NotificationChannelCreate, NotificationChannelUpdate, NotificationChannelPublic, NotificationChannelsPublic,
    NotificationRule, NotificationRuleCreate, NotificationRuleUpdate, NotificationRulePublic, NotificationRulesPublic,
    NotificationLog, NotificationLogPublic, NotificationLogsPublic,
    TestNotificationRequest, TestNotificationResponse,
    ChannelType, TriggerType, NotificationStatus,
)
from app.models.scheduled_task import (
    ScheduledTask, ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTaskPublic, ScheduledTasksPublic,
    TaskExecutionLog, TaskExecutionLogPublic, TaskExecutionLogsPublic,
)
from app.models.defect import (
    Defect, DefectCreate, DefectUpdate, DefectPublic, DefectsPublic, DefectStats,
    DefectSeverity, DefectSource, ErrorType, DefectTrend, DefectBatchCreate, DefectDedupResult,
)
from app.models.defect_import import (
    DefectImportRecord, ImportPlatform, ImportStatus, ImportPreview, ImportResult,
    FieldMappingRule, DefectImportTemplate,
)
from app.models.base import CHINA_TZ, get_datetime_china
from pydantic import BaseModel

# Token 相关模型
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


class Message(BaseModel):
    message: str


class NewPassword(BaseModel):
    token: str
    new_password: str


__all__ = [
    "CHINA_TZ", "get_datetime_china",
    "User", "UserBase", "UserCreate", "UserRegister", "UserUpdate", "UserUpdateMe", "UpdatePassword", "UserPublic", "UsersPublic",
    "Item", "ItemBase", "ItemCreate", "ItemUpdate", "ItemPublic", "ItemsPublic",
    "TestExecution", "TestExecutionCreate", "TestExecutionUpdate", "TestExecutionPublic", "TestExecutionsPublic",
    "Project", "ProjectCreate", "ProjectUpdate", "ProjectPublic", "ProjectsPublic", "ProjectStats",
    "Collection", "CollectionCreate", "CollectionUpdate", "CollectionPublic", "CollectionsPublic",
    "AuditLog", "AuditLogPublic", "AuditLogsPublic",
    "NotificationChannel", "NotificationChannelCreate", "NotificationChannelUpdate", "NotificationChannelPublic", "NotificationChannelsPublic",
    "NotificationRule", "NotificationRuleCreate", "NotificationRuleUpdate", "NotificationRulePublic", "NotificationRulesPublic",
    "NotificationLog", "NotificationLogPublic", "NotificationLogsPublic",
    "TestNotificationRequest", "TestNotificationResponse",
    "ChannelType", "TriggerType", "NotificationStatus",
    "ScheduledTask", "ScheduledTaskCreate", "ScheduledTaskUpdate", "ScheduledTaskPublic", "ScheduledTasksPublic",
    "TaskExecutionLog", "TaskExecutionLogPublic", "TaskExecutionLogsPublic",
    "Defect", "DefectCreate", "DefectUpdate", "DefectPublic", "DefectsPublic", "DefectStats",
    "DefectSeverity", "DefectSource", "ErrorType", "DefectTrend", "DefectBatchCreate", "DefectDedupResult",
    "DefectImportRecord", "ImportPlatform", "ImportStatus", "ImportPreview", "ImportResult",
    "FieldMappingRule", "DefectImportTemplate",
    "Token", "TokenPayload", "Message", "NewPassword",
    "SQLModel",
]
