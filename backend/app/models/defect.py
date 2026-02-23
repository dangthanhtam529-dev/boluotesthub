"""
缺陷管理数据模型

设计理念：
- 收集：从接口测试失败、手动录入、文件导入三个渠道收集
- 分析：分类、标签、去重、趋势分析
- 预留：大模型处理字段

核心变化：
- 移除生命周期状态（不做修复跟踪）
- 移除指派功能
- 添加来源追踪
- 添加原始数据保存
- 添加去重机制
"""

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Text
from sqlmodel import Field, SQLModel


class DefectSource(str, Enum):
    """缺陷来源"""
    MANUAL = "manual"
    EXECUTION = "execution"
    IMPORT = "import"


SOURCE_LABELS = {
    DefectSource.MANUAL: "手动录入",
    DefectSource.EXECUTION: "执行失败",
    DefectSource.IMPORT: "文件导入",
}


class DefectSeverity(str, Enum):
    """缺陷严重程度"""
    CRITICAL = "critical"
    MAJOR = "major"
    NORMAL = "normal"
    MINOR = "minor"
    SUGGESTION = "suggestion"


SEVERITY_LABELS = {
    DefectSeverity.CRITICAL: "致命",
    DefectSeverity.MAJOR: "严重",
    DefectSeverity.NORMAL: "一般",
    DefectSeverity.MINOR: "轻微",
    DefectSeverity.SUGGESTION: "建议",
}


class ErrorType(str, Enum):
    """错误类型"""
    ASSERTION_FAILED = "assertion_failed"
    TIMEOUT = "timeout"
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    NETWORK_ERROR = "network_error"
    SCHEMA_ERROR = "schema_error"
    DATA_ERROR = "data_error"
    OTHER = "other"


ERROR_TYPE_LABELS = {
    ErrorType.ASSERTION_FAILED: "断言失败",
    ErrorType.TIMEOUT: "请求超时",
    ErrorType.HTTP_4XX: "客户端错误(4xx)",
    ErrorType.HTTP_5XX: "服务端错误(5xx)",
    ErrorType.NETWORK_ERROR: "网络错误",
    ErrorType.SCHEMA_ERROR: "响应结构错误",
    ErrorType.DATA_ERROR: "数据错误",
    ErrorType.OTHER: "其他",
}


def generate_fingerprint(
    api_path: str | None,
    api_method: str | None,
    error_type: str | None,
    error_message: str | None,
) -> str:
    """
    生成缺陷指纹，用于去重
    
    基于以下字段生成唯一标识：
    - API路径
    - HTTP方法
    - 错误类型
    - 错误信息（截取前200字符）
    """
    raw = f"{api_path or ''}|{api_method or ''}|{error_type or ''}|{(error_message or '')[:200]}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class Defect(SQLModel, table=True):
    """
    缺陷数据模型
    
    核心字段分组：
    1. 基础信息：标题、描述、项目
    2. 来源信息：来源类型、关联ID
    3. 定位信息：API路径、方法、模块、错误类型
    4. 原始数据：请求、响应、错误详情
    5. 分类分析：严重程度、标签
    6. 去重机制：指纹、重复次数
    7. 大模型预留：分析结果、建议
    """
    __tablename__ = "defects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    title: str = Field(max_length=200, description="缺陷标题")
    description: str | None = Field(default=None, sa_type=Text, description="缺陷描述")

    source: str = Field(default=DefectSource.MANUAL.value, max_length=20, description="来源类型")
    source_id: str | None = Field(default=None, max_length=100, description="关联来源ID")

    api_path: str | None = Field(default=None, max_length=500, description="API路径")
    api_method: str | None = Field(default=None, max_length=10, description="HTTP方法")
    module: str | None = Field(default=None, max_length=100, description="所属模块")
    error_type: str | None = Field(default=None, max_length=50, description="错误类型")

    request_data: str | None = Field(default=None, sa_type=Text, description="原始请求数据(JSON)")
    response_data: str | None = Field(default=None, sa_type=Text, description="原始响应数据(JSON)")
    error_detail: str | None = Field(default=None, sa_type=Text, description="错误详情")

    severity: str = Field(default=DefectSeverity.NORMAL.value, max_length=20, description="严重程度")
    tags: str | None = Field(default=None, sa_type=Text, description="标签(JSON数组)")

    fingerprint: str | None = Field(default=None, max_length=32, index=True, description="去重指纹")
    occurrence_count: int = Field(default=1, description="重复出现次数")

    ai_analysis: str | None = Field(default=None, sa_type=Text, description="AI分析结果(预留)")
    ai_suggestion: str | None = Field(default=None, sa_type=Text, description="AI建议(预留)")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class DefectCreate(SQLModel):
    """创建缺陷请求"""
    title: str = Field(max_length=200)
    description: str | None = None

    source: str = Field(default=DefectSource.MANUAL.value)
    source_id: str | None = None

    api_path: str | None = None
    api_method: str | None = None
    module: str | None = None
    error_type: str | None = None

    request_data: str | None = None
    response_data: str | None = None
    error_detail: str | None = None

    severity: str = Field(default=DefectSeverity.NORMAL.value)
    tags: list[str] | None = None

    fingerprint: str | None = None


class DefectUpdate(SQLModel):
    """更新缺陷请求"""
    title: str | None = None
    description: str | None = None

    module: str | None = None
    error_type: str | None = None

    severity: str | None = None
    tags: list[str] | None = None

    ai_analysis: str | None = None
    ai_suggestion: str | None = None


class DefectPublic(SQLModel):
    """缺陷公开信息"""
    id: uuid.UUID
    project_id: uuid.UUID

    title: str
    description: str | None

    source: str
    source_id: str | None

    api_path: str | None
    api_method: str | None
    module: str | None
    error_type: str | None

    request_data: str | None
    response_data: str | None
    error_detail: str | None

    severity: str
    tags: list[str] | None

    fingerprint: str | None
    occurrence_count: int

    ai_analysis: str | None
    ai_suggestion: str | None

    created_at: datetime
    updated_at: datetime


class DefectsPublic(SQLModel):
    """缺陷列表响应"""
    data: list[DefectPublic]
    count: int


class DefectStats(SQLModel):
    """缺陷统计"""
    total: int = 0

    by_source: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_error_type: dict[str, int] = {}
    by_module: dict[str, int] = {}

    recent_count: int = 0
    duplicate_count: int = 0


class DefectTrend(SQLModel):
    """缺陷趋势"""
    date: str
    count: int
    by_severity: dict[str, int] = {}


class DefectBatchCreate(SQLModel):
    """批量创建缺陷（用于导入）"""
    defects: list[DefectCreate]
    source: str = Field(default=DefectSource.IMPORT.value)
    source_id: str | None = None


class DefectDedupResult(SQLModel):
    """去重结果"""
    new_count: int
    duplicate_count: int
    error_count: int = 0
    total_count: int
    details: list[dict[str, Any]]
