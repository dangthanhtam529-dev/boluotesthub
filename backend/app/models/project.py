"""
项目模型模块 (Project Models)

本模块定义了项目和测试集合相关的数据模型，包括：
1. 项目（Project）- 测试项目的容器
2. 测试集合（Collection）- 测试套件和场景的组织单元

项目与 Apifox 的关系：
┌─────────────────────────────────────────────────────────────┐
│                    Apifox 平台                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Apifox Project (apifox_project_id)                 │    │
│  │  ├── Test Suite 1                                   │    │
│  │  │   ├── API Test 1                                │    │
│  │  │   └── API Test 2                                │    │
│  │  ├── Test Suite 2                                   │    │
│  │  └── Test Scenario 1                                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 同步
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    本地数据库                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Project (id, owner_id)                             │    │
│  │  ├── Collection 1 (apifox_collection_id)           │    │
│  │  ├── Collection 2                                   │    │
│  │  └── Collection 3                                   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

数据隔离策略：
- 每个项目独立管理测试集合
- 执行记录按项目隔离
- 测试报告存储在 MongoDB，按 project_id 索引
"""

from __future__ import annotations
import enum
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel
from sqlalchemy import DateTime, Text
from app.models.base import get_datetime_china


# ============================================================================
# 枚举类型
# ============================================================================
class CollectionType(str, enum.Enum):
    """
    测试集合类型枚举
    
    Apifox 支持多种测试类型：
    - TEST_SUITE: 测试套件，包含多个 API 测试
    - TEST_SCENARIO: 测试场景，按顺序执行的测试流程
    - TEST_SCENARIO_FOLDER: 测试场景文件夹，用于组织场景
    
    使用枚举的好处：
    1. 类型安全，避免拼写错误
    2. IDE 自动补全支持
    3. 数据库存储为字符串，可读性好
    """
    TEST_SUITE = "test-suite"
    TEST_SCENARIO = "test-scenario"
    TEST_SCENARIO_FOLDER = "test-scenario-folder"


# ============================================================================
# 项目模型
# ============================================================================
class ProjectBase(SQLModel):
    """
    项目基础属性模型
    
    项目是测试管理的顶层容器，用于：
    1. 组织测试集合
    2. 关联 Apifox 项目
    3. 隔离测试数据和报告
    
    属性：
    - name: 项目名称，必填
    - description: 项目描述，可选
    - apifox_project_id: 关联的 Apifox 项目 ID，用于同步
    """
    name: str = Field(max_length=255, description="项目名称")
    description: str | None = Field(default=None, max_length=1000, description="项目描述")
    apifox_project_id: str | None = Field(default=None, max_length=100, description="Apifox 项目ID")


class ProjectCreate(ProjectBase):
    """
    创建项目请求模型
    
    继承 ProjectBase 的所有属性。
    
    使用场景：
    - POST /api/v1/projects/ - 创建新项目
    
    数据流程：
    1. 前端提交项目信息
    2. 后端创建项目记录
    3. 自动设置 owner_id 为当前用户
    """
    pass


class ProjectUpdate(SQLModel):
    """
    更新项目请求模型
    
    所有字段可选，支持部分更新。
    
    使用场景：
    - PATCH /api/v1/projects/{project_id} - 更新项目
    
    可更新字段：
    - name: 项目名称
    - description: 项目描述
    - apifox_project_id: Apifox 项目 ID
    - is_active: 是否启用
    """
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    apifox_project_id: str | None = Field(default=None, max_length=100)
    is_active: bool | None = Field(default=None)


class Project(ProjectBase, table=True):
    """
    项目数据库模型
    
    映射到数据库表 "projects"，存储项目信息。
    
    表结构：
    ┌──────────────────┬─────────────┬──────────────────────────┐
    │ 字段名            │ 类型        │ 说明                      │
    ├──────────────────┼─────────────┼──────────────────────────┤
    │ id               │ UUID        │ 主键                      │
    │ name             │ VARCHAR(255)│ 项目名称                  │
    │ description      │ VARCHAR(1000)│ 项目描述                 │
    │ owner_id         │ UUID        │ 创建者ID（外键）          │
    │ apifox_project_id│ VARCHAR(100)│ Apifox 项目ID            │
    │ is_active        │ BOOLEAN     │ 是否启用                  │
    │ settings         │ TEXT        │ 项目配置（JSON）          │
    │ last_sync_at     │ DATETIME    │ 最后同步时间              │
    │ created_at       │ DATETIME    │ 创建时间                  │
    │ updated_at       │ DATETIME    │ 更新时间                  │
    └──────────────────┴─────────────┴──────────────────────────┘
    
    关系：
    - owner: User (多对一，一个用户可有多个项目)
    - collections: Collection (一对多，一个项目可有多个集合)
    - executions: TestExecution (一对多，一个项目可有多个执行记录)
    """
    __tablename__ = "projects"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # 外键关联到 user 表
    # index=True 表示创建索引，加速按 owner_id 查询
    owner_id: uuid.UUID = Field(foreign_key="user.id", index=True, description="创建者ID")
    
    is_active: bool = Field(default=True, description="是否启用")
    
    # 项目配置，存储为 JSON 字符串
    # 可包含：默认环境、通知设置、自定义参数等
    settings: str | None = Field(default=None, sa_type=Text, description="项目配置(JSON)")
    
    # 记录最后一次从 Apifox 同步的时间
    # 用于判断是否需要重新同步
    last_sync_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="最后同步时间"
    )
    
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )


class ProjectPublic(ProjectBase):
    """
    项目公开信息响应模型
    
    返回给前端的项目数据，包含额外统计信息。
    
    额外字段：
    - id: 项目 ID
    - owner_id: 创建者 ID
    - is_active: 是否启用
    - last_sync_at: 最后同步时间
    - created_at: 创建时间
    - updated_at: 更新时间
    - collection_count: 测试集合数量（计算字段）
    - execution_count: 执行记录数量（计算字段）
    
    返回示例：
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "API 测试项目",
        "description": "主要 API 接口测试",
        "apifox_project_id": "123456",
        "owner_id": "...",
        "is_active": true,
        "collection_count": 10,
        "execution_count": 50,
        ...
    }
    """
    id: uuid.UUID
    owner_id: uuid.UUID
    is_active: bool
    last_sync_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    # 统计字段（在查询时计算）
    collection_count: int = 0
    execution_count: int = 0


class ProjectsPublic(SQLModel):
    """
    项目列表响应模型
    
    用于分页返回多个项目。
    """
    data: list[ProjectPublic]
    count: int


# ============================================================================
# 测试集合模型
# ============================================================================
class CollectionBase(SQLModel):
    """
    测试集合基础属性模型
    
    测试集合是从 Apifox 同步的测试套件或场景。
    
    属性：
    - name: 集合名称
    - apifox_collection_id: Apifox 中的集合 ID（用于关联）
    - collection_type: 集合类型（test-suite/test-scenario）
    - description: 描述信息
    """
    name: str = Field(max_length=255, description="集合名称")
    apifox_collection_id: str = Field(max_length=100, description="Apifox 集合ID")
    collection_type: str = Field(default="test-suite", max_length=50, description="集合类型")
    description: str | None = Field(default=None, max_length=1000, description="描述")


class CollectionCreate(CollectionBase):
    """
    创建测试集合请求模型
    
    需要指定所属项目。
    
    使用场景：
    - 从 Apifox 同步时创建
    - 手动创建测试集合
    """
    project_id: uuid.UUID


class CollectionUpdate(SQLModel):
    """
    更新测试集合请求模型
    
    所有字段可选，支持部分更新。
    """
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    environment_ids: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class Collection(CollectionBase, table=True):
    """
    测试集合数据库模型
    
    映射到数据库表 "collections"，存储测试集合信息。
    
    表结构：
    ┌────────────────────────┬─────────────┬──────────────────────┐
    │ 字段名                  │ 类型        │ 说明                  │
    ├────────────────────────┼─────────────┼──────────────────────┤
    │ id                     │ UUID        │ 主键                  │
    │ project_id             │ UUID        │ 所属项目ID（外键）    │
    │ name                   │ VARCHAR(255)│ 集合名称              │
    │ apifox_collection_id   │ VARCHAR(100)│ Apifox 集合ID        │
    │ collection_type        │ VARCHAR(50) │ 集合类型              │
    │ description            │ VARCHAR(1000)│ 描述                 │
    │ environment_ids        │ TEXT        │ 可用环境ID列表(JSON)  │
    │ is_active              │ BOOLEAN     │ 是否启用              │
    │ created_at             │ DATETIME    │ 创建时间              │
    │ updated_at             │ DATETIME    │ 更新时间              │
    └────────────────────────┴─────────────┴──────────────────────┘
    
    关系：
    - project: Project (多对一，一个项目可有多个集合)
    - executions: TestExecution (一对多，一个集合可执行多次)
    """
    __tablename__ = "collections"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # 外键关联到 projects 表
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True, description="所属项目ID")
    
    # 可用环境 ID 列表，存储为 JSON 数组字符串
    # 例如：["env_1", "env_2", "env_3"]
    environment_ids: str | None = Field(default=None, sa_type=Text, description="可用环境ID列表(JSON)")
    
    is_active: bool = Field(default=True, description="是否启用")
    
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )


class CollectionPublic(CollectionBase):
    """
    测试集合公开信息响应模型
    
    包含执行统计信息。
    """
    id: uuid.UUID
    project_id: uuid.UUID
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    # 统计字段
    execution_count: int = 0
    last_execution_at: datetime | None = None


class CollectionsPublic(SQLModel):
    """
    测试集合列表响应模型
    """
    data: list[CollectionPublic]
    count: int


# ============================================================================
# 统计模型
# ============================================================================
class ProjectStats(SQLModel):
    """
    项目统计信息模型
    
    用于项目概览页面，展示关键指标。
    
    属性：
    - total_collections: 测试集合总数
    - total_executions: 执行总次数
    - total_passed: 通过次数
    - total_failed: 失败次数
    - pass_rate: 通过率（0-1 之间的小数）
    - recent_executions: 最近执行记录列表
    """
    total_collections: int
    total_executions: int
    total_passed: int
    total_failed: int
    pass_rate: float
    recent_executions: list[dict]
