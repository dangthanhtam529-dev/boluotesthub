# 测试执行相关模型
from __future__ import annotations
import enum
import uuid
from datetime import datetime
from pydantic import computed_field
from sqlmodel import Field, SQLModel
from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from app.models.base import get_datetime_china


# ============ 枚举类型 ============
class ExecutionStatus(str, enum.Enum):
    """执行状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


# ============ 基础属性 ============
class TestExecutionBase(SQLModel):
    """测试执行基础属性"""
    project_id: uuid.UUID | None = Field(default=None, foreign_key="projects.id", description="所属项目ID")
    apifox_collection_id: str = Field(index=True, description="Apifox 测试集合 ID")
    project_name: str | None = Field(default=None, max_length=255, description="项目名称（可选）")
    environment: str | None = Field(default=None, max_length=100, description="执行环境")
    collection_type: str | None = Field(default=None, max_length=50, description="集合类型: test-suite 或 test-scenario")


# ============ 创建/更新 ============
class TestExecutionCreate(TestExecutionBase):
    """创建测试执行时接收的数据"""
    pass


class TestExecutionUpdate(SQLModel):
    """更新测试执行时接收的数据"""
    project_name: str | None = Field(default=None, max_length=255)
    environment: str | None = Field(default=None, max_length=100)


# ============ 数据库模型 ============
class TestExecution(TestExecutionBase, table=True):
    """测试执行数据库模型"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # 执行状态
    status: str = Field(default=ExecutionStatus.PENDING, description="执行状态")
    
    # 执行结果统计
    total_cases: int | None = Field(default=None, description="总用例数")
    passed_cases: int | None = Field(default=None, description="通过数")
    failed_cases: int | None = Field(default=None, description="失败数")
    
    # 执行耗时（秒）
    duration: float | None = Field(default=None, description="执行耗时（秒）")
    
    # 时间戳
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="开始执行时间"
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="执行完成时间"
    )
    
    # 错误信息
    error_message: str | None = Field(default=None, description="错误信息（执行失败时）")
    
    # 详细报告（JSON 格式存储）- 使用 LONGTEXT 类型支持大报告
    report_json: str | None = Field(
        default=None,
        sa_type=LONGTEXT,
        description="Apifox 返回的完整报告（JSON）- 已迁移到 MongoDB，此字段保留兼容"
    )
    
    # MongoDB 关联
    mongo_report_id: str | None = Field(
        default=None,
        description="MongoDB 报告文档 ID"
    )
    has_mongodb_report: bool = Field(
        default=False,
        description="是否有 MongoDB 存储的详细报告"
    )
    
    # 性能指标（便于快速查询）
    response_time_avg: float | None = Field(
        default=None,
        description="平均响应时间（毫秒）"
    )
    response_time_max: float | None = Field(
        default=None,
        description="最大响应时间（毫秒）"
    )
    response_time_min: float | None = Field(
        default=None,
        description="最小响应时间（毫秒）"
    )
    
    # 错误摘要（前 200 字符，便于列表展示）
    error_summary: str | None = Field(
        default=None,
        max_length=200,
        description="错误摘要（前 200 字符）"
    )


# ============ 响应模型 ============
class TestExecutionPublic(TestExecutionBase):
    """返回给前端的测试执行数据"""
    id: uuid.UUID
    status: str
    total_cases: int | None = None
    passed_cases: int | None = None
    failed_cases: int | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    duration: float | None = None
    
    # MongoDB 关联
    mongo_report_id: str | None = None
    has_mongodb_report: bool = False
    
    # 性能指标
    response_time_avg: float | None = None
    response_time_max: float | None = None
    response_time_min: float | None = None
    error_summary: str | None = None
    
    # 计算属性
    @computed_field
    @property
    def pass_rate(self) -> float | None:
        """计算通过率"""
        if self.total_cases and self.total_cases > 0:
            return round((self.passed_cases or 0) / self.total_cases * 100, 2)
        return None
    
    @computed_field
    @property
    def duration_seconds(self) -> int | None:
        """计算执行耗时（秒）"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class TestExecutionsPublic(SQLModel):
    """测试执行列表响应"""
    data: list[TestExecutionPublic]
    count: int


# ============ 执行统计 ============
class ExecutionStats(SQLModel):
    """执行统计数据"""
    total_executions: int
    total_passed: int
    total_failed: int
    pass_rate: float
    recent_executions: list[TestExecutionPublic]