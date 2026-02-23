"""
缺陷导入数据模型

支持从外部平台导入缺陷数据：
- Jira
- Tapd
- 禅道
- Excel
- JSON
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Text
from sqlmodel import Field, SQLModel


class ImportPlatform(str, Enum):
    """导入平台"""
    JIRA = "jira"
    TAPD = "tapd"
    ZENTAO = "zentao"
    EXCEL = "excel"
    JSON = "json"
    OTHER = "other"


PLATFORM_LABELS = {
    ImportPlatform.JIRA: "Jira",
    ImportPlatform.TAPD: "Tapd",
    ImportPlatform.ZENTAO: "禅道",
    ImportPlatform.EXCEL: "Excel",
    ImportPlatform.JSON: "JSON",
    ImportPlatform.OTHER: "其他",
}


class ImportStatus(str, Enum):
    """导入状态"""
    PENDING = "pending"
    PARSING = "parsing"
    MAPPING = "mapping"
    CONFIRMING = "confirming"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


STATUS_LABELS = {
    ImportStatus.PENDING: "待处理",
    ImportStatus.PARSING: "解析中",
    ImportStatus.MAPPING: "字段映射",
    ImportStatus.CONFIRMING: "待确认",
    ImportStatus.IMPORTING: "导入中",
    ImportStatus.COMPLETED: "已完成",
    ImportStatus.FAILED: "失败",
}


class DefectImportRecord(SQLModel, table=True):
    """
    缺陷导入记录
    
    记录每次导入的详细信息
    """
    __tablename__ = "defect_import_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    platform: str = Field(max_length=20, description="导入平台")
    file_name: str = Field(max_length=255, description="文件名")
    file_size: int = Field(default=0, description="文件大小(字节)")

    status: str = Field(default=ImportStatus.PENDING.value, max_length=20, description="导入状态")
    
    total_count: int = Field(default=0, description="总记录数")
    new_count: int = Field(default=0, description="新增数")
    duplicate_count: int = Field(default=0, description="重复数")
    error_count: int = Field(default=0, description="错误数")
    
    parsed_data: str | None = Field(default=None, sa_type=Text, description="解析后的数据(JSON)")
    field_mapping: str | None = Field(default=None, sa_type=Text, description="字段映射配置(JSON)")
    error_detail: str | None = Field(default=None, sa_type=Text, description="错误详情")
    
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")


class FieldMappingRule(SQLModel):
    """字段映射规则"""
    source_field: str
    target_field: str
    transform: str | None = None


class ImportPreview(SQLModel):
    """导入预览"""
    record_id: str | None = None
    total_count: int = 0
    new_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    preview_data: list[dict[str, Any]] = []
    field_mapping: dict[str, str] = {}
    errors: list[dict[str, Any]] = []


class ImportResult(SQLModel):
    """导入结果"""
    record_id: str
    status: str
    total_count: int = 0
    new_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    details: list[dict[str, Any]] = []


class DefectImportTemplate(SQLModel):
    """导入模板"""
    platform: str
    fields: list[dict[str, Any]]
    sample_data: list[dict[str, Any]]


class ImportRecordPublic(SQLModel):
    """导入记录公开模型"""
    id: str
    platform: str
    platform_label: str
    file_name: str
    file_size: int
    status: str
    total_count: int
    new_count: int
    duplicate_count: int
    error_count: int
    created_at: str | None
    completed_at: str | None


class ImportRecordsPublic(SQLModel):
    """导入记录列表"""
    data: list[ImportRecordPublic]
    count: int


class PlatformOption(SQLModel):
    """平台选项"""
    value: str
    label: str


JIRA_FIELD_MAPPING = {
    "summary": "title",
    "description": "description",
    "priority": "severity",
    "labels": "tags",
    "created": "created_at",
    "updated": "updated_at",
    "issuetype": "error_type",
    "components": "module",
}

TAPD_FIELD_MAPPING = {
    "title": "title",
    "description": "description",
    "priority": "severity",
    "category": "error_type",
    "workitem_type": "module",
    "created": "created_at",
    "modified": "updated_at",
}

ZENTAO_FIELD_MAPPING = {
    # Bug编号 → source_id（外部ID）
    "Bug编号": "source_id",
    "bug编号": "source_id",
    "编号": "source_id",
    "ID": "source_id",
    "id": "source_id",
    "缺陷编号": "source_id",
    "工作项编号": "source_id",
    # Bug标题 → title
    "Bug标题": "title",
    "bug标题": "title",
    "标题": "title",
    "title": "title",
    "summary": "title",
    "缺陷标题": "title",
    "工作项标题": "title",
    "名称": "title",
    # 重现步骤/描述 → description
    "重现步骤": "description",
    "步骤": "description",
    "Bug描述": "description",
    "描述": "description",
    "description": "description",
    "详细描述": "description",
    "缺陷描述": "description",
    "复现步骤": "description",
    # 严重程度 → severity
    "严重程度": "severity",
    "severity": "severity",
    "优先级": "severity",
    "priority": "severity",
    "严重性": "severity",
    "等级": "severity",
    # Bug类型 → error_type
    "Bug类型": "error_type",
    "bug类型": "error_type",
    "类型": "error_type",
    "error_type": "error_type",
    "缺陷类型": "error_type",
    "错误类型": "error_type",
    "工作项类型": "error_type",
    # 所属模块 → module
    "所属模块": "module",
    "模块": "module",
    "module": "module",
    "所属产品": "module",
    "产品": "module",
    "组件": "module",
    "功能模块": "module",
    # 关键词 → tags
    "关键词": "tags",
    "tags": "tags",
    "标签": "tags",
    "labels": "tags",
    "keywords": "tags",
}

EXCEL_FIELD_MAPPING = {
    # 复用禅道的全部映射，因为 Excel 导出的列名可能和禅道一样
    **ZENTAO_FIELD_MAPPING,
    # Excel 特有的列名
    "API路径": "api_path",
    "接口路径": "api_path",
    "api_path": "api_path",
    "请求方法": "api_method",
    "api_method": "api_method",
    "错误类型": "error_type",
    "错误详情": "error_detail",
}

SEVERITY_MAPPING = {
    # 英文
    "highest": "critical",
    "high": "major",
    "medium": "normal",
    "low": "minor",
    "lowest": "suggestion",
    "critical": "critical",
    "major": "major",
    "normal": "normal",
    "minor": "minor",
    "suggestion": "suggestion",
    "blocker": "critical",
    "trivial": "minor",
    # 中文
    "致命": "critical",
    "严重": "major",
    "一般": "normal",
    "轻微": "minor",
    "建议": "suggestion",
    "紧急": "critical",
    "主要": "major",
    "次要": "minor",
    "提示": "suggestion",
    "高": "major",
    "中": "normal",
    "低": "minor",
    # P级别
    "P0": "critical",
    "P1": "major",
    "P2": "normal",
    "P3": "minor",
    "P4": "suggestion",
    "p0": "critical",
    "p1": "major",
    "p2": "normal",
    "p3": "minor",
    "p4": "suggestion",
    # 数字
    "1": "critical",
    "2": "major",
    "3": "normal",
    "4": "minor",
    "5": "suggestion",
    "1级": "critical",
    "2级": "major",
    "3级": "normal",
    "4级": "minor",
    "5级": "suggestion",
    # S级别（云效）
    "S1": "critical",
    "S2": "major",
    "S3": "normal",
    "S4": "minor",
    "s1": "critical",
    "s2": "major",
    "s3": "normal",
    "s4": "minor",
}

ERROR_TYPE_MAPPING = {
    # 英文
    "bug": "other",
    "task": "other",
    "story": "other",
    "defect": "other",
    "assertion_failed": "assertion_failed",
    "timeout": "timeout",
    "http_4xx": "http_4xx",
    "http_5xx": "http_5xx",
    "network_error": "network_error",
    "schema_error": "schema_error",
    "data_error": "data_error",
    "other": "other",
    # 中文
    "代码错误": "other",
    "功能缺陷": "other",
    "界面优化": "other",
    "设计缺陷": "other",
    "配置相关": "other",
    "安装部署": "other",
    "安全相关": "other",
    "性能问题": "timeout",
    "断言失败": "assertion_failed",
    "超时": "timeout",
    "接口错误": "http_5xx",
    "数据错误": "data_error",
    "网络错误": "network_error",
    "服务端错误": "http_5xx",
    "客户端错误": "http_4xx",
    "响应错误": "schema_error",
    # 禅道 Bug 类型
    "代码错误": "other",
    "界面优化": "other",
    "设计缺陷": "other",
    "其他": "other",
    "需求变更": "other",
}
