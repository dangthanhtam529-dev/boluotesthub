"""
基础模型模块 (Base Models)

本模块定义了所有数据模型的基类，提供：
1. 通用字段（id, created_at）
2. 时区处理（中国标准时间 UTC+8）
3. 类型提示和验证

模型继承关系：
┌─────────────────────────────────────────────────────────────┐
│                      SQLModel                                │
│                    (Pydantic + SQLAlchemy)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      BaseModel                               │
│              (基础模型，用于 API Schema)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     BaseDBModel                              │
│          (数据库模型，包含 id 和 created_at)                 │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           User        Project      Execution
           ...          ...           ...

SQLModel 说明：
- 结合了 Pydantic（数据验证）和 SQLAlchemy（ORM）
- 一个类同时定义了数据库表结构和 API Schema
- 支持类型提示，IDE 自动补全友好
"""

import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

# ============================================================================
# 时区配置
# ============================================================================
# 中国标准时间：UTC+8
# 使用 timezone 对象而不是字符串，避免时区解析问题
#
# 为什么需要时区？
# 1. 服务器可能部署在不同时区
# 2. 用户需要看到本地时间
# 3. 日志和数据分析需要统一的时间基准
#
# 时区处理策略：
# - 数据库存储：带时区的时间戳
# - API 返回：ISO 8601 格式（包含时区信息）
# - 前端显示：转换为用户本地时间
CHINA_TZ = timezone(timedelta(hours=8))


def get_datetime_china() -> datetime:
    """
    获取中国标准时间（UTC+8）
    
    用于模型的 created_at 字段默认值。
    
    Returns:
        datetime: 当前中国标准时间，带时区信息
    
    示例：
        >>> get_datetime_china()
        datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone(timedelta(hours=8)))
    
    注意：
    - 返回的是带时区信息的 datetime 对象
    - 数据库存储时会保留时区信息
    - JSON 序列化时会转换为 ISO 8601 格式
    """
    return datetime.now(CHINA_TZ)


# ============================================================================
# 基础模型类
# ============================================================================
class BaseModel(SQLModel):
    """
    基础模型类
    
    用于定义 API 请求/响应的 Schema，不包含数据库字段。
    
    用途：
    - API 请求体验证（如 UserCreate, ProjectUpdate）
    - API 响应体格式化（如 UserPublic, ProjectPublic）
    - 通用数据传输对象
    
    示例：
        class UserCreate(BaseModel):
            email: EmailStr
            password: str
    
    注意：
    - 此类不映射到数据库表
    - 子类可以添加任意字段
    - 继承自 SQLModel 以获得 Pydantic 验证功能
    """
    pass


class BaseDBModel(SQLModel):
    """
    数据库基础模型类
    
    所有数据库表的基类，包含通用字段：
    - id: UUID 主键
    - created_at: 创建时间
    
    字段说明：
    
    id (UUID):
    - 使用 UUID 而不是自增整数的原因：
      1. 分布式系统友好（可在应用层生成）
      2. 不会暴露数据量
      3. 合并数据时不会冲突
      4. URL 友好（可以编码为字符串）
    
    created_at (datetime):
    - 记录创建时间，用于：
      1. 数据排序
      2. 审计追踪
      3. 数据分析
    - 使用中国时区
    - 带时区信息存储
    
    使用示例：
        class User(BaseDBModel, table=True):
            __tablename__ = "user"
            email: str = Field(unique=True, index=True)
            hashed_password: str
            is_active: bool = True
    
    注意：
    - 子类需要设置 table=True 才能映射到数据库表
    - 子类需要设置 __tablename__ 指定表名
    - 多继承时，BaseDBModel 应放在前面
    """
    
    # UUID 主键
    # default_factory=uuid.uuid4 表示创建对象时自动生成 UUID
    # primary_key=True 表示这是主键
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # 创建时间
    # default_factory=get_datetime_china 表示创建对象时自动获取当前时间
    # sa_type=DateTime(timezone=True) 告诉 SQLAlchemy 这是带时区的日期时间类型
    # | None 表示这个字段可以是 None（用于某些场景）
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )
