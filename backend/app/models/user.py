"""
用户模型模块 (User Models)

本模块定义了用户相关的所有数据模型，包括：
1. 数据库表模型（User）
2. API 请求模型（UserCreate, UserUpdate）
3. API 响应模型（UserPublic, UsersPublic）

模型分类说明：
┌─────────────────────────────────────────────────────────────┐
│                    用户模型分类                              │
├─────────────────────────────────────────────────────────────┤
│  数据库模型 (table=True)                                     │
│  └── User - 用户表，存储用户账号信息                        │
├─────────────────────────────────────────────────────────────┤
│  请求模型 (用于接收前端数据)                                 │
│  ├── UserCreate    - 管理员创建用户                         │
│  ├── UserRegister  - 用户自主注册                           │
│  ├── UserUpdate    - 管理员更新用户                         │
│  ├── UserUpdateMe  - 用户更新自己                           │
│  └── UpdatePassword - 修改密码                              │
├─────────────────────────────────────────────────────────────┤
│  响应模型 (用于返回给前端)                                   │
│  ├── UserPublic   - 单个用户信息                            │
│  └── UsersPublic  - 用户列表（带分页）                      │
└─────────────────────────────────────────────────────────────┘

安全考虑：
- 密码不在响应模型中返回
- 密码存储为哈希值（hashed_password）
- 密码长度限制（8-128字符）
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel
from app.models.base import get_datetime_china

# TYPE_CHECKING 用于类型检查时导入，运行时不导入
# 避免循环导入问题
if TYPE_CHECKING:
    from app.models.item import Item


# ============================================================================
# 基础属性模型
# ============================================================================
class UserBase(SQLModel):
    """
    用户基础属性模型
    
    包含用户的核心属性，被其他模型继承：
    - UserCreate: 创建用户时继承
    - UserUpdate: 更新用户时继承
    - User: 数据库模型继承
    
    属性说明：
    - email: 用户邮箱，唯一标识，用于登录
    - is_active: 是否激活，禁用用户无法登录
    - is_superuser: 是否超级管理员，拥有所有权限
    - full_name: 用户全名，可选
    
    字段约束：
    - email: 必须是有效邮箱格式，唯一，建立索引加速查询
    - full_name: 最大255字符
    """
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# ============================================================================
# 创建/注册模型
# ============================================================================
class UserCreate(UserBase):
    """
    创建用户请求模型
    
    用于管理员创建新用户，继承 UserBase 的所有属性。
    
    额外属性：
    - password: 用户密码（明文），会被哈希后存储
    
    验证规则：
    - password: 最少8字符，最多128字符
    
    使用场景：
    - POST /api/v1/users/ - 管理员创建用户
    
    数据流程：
    1. 前端提交 UserCreate（包含明文密码）
    2. 后端验证数据格式
    3. 对密码进行哈希处理
    4. 创建 User 数据库记录（存储 hashed_password）
    """
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    """
    用户自主注册请求模型
    
    与 UserCreate 的区别：
    - 不包含 is_active（默认激活）
    - 不包含 is_superuser（不能自己设为管理员）
    
    这确保了用户注册时不能给自己分配特殊权限。
    
    使用场景：
    - POST /api/v1/users/signup - 用户自主注册
    
    属性：
    - email: 注册邮箱
    - password: 设置密码
    - full_name: 用户名（可选）
    """
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# ============================================================================
# 更新模型
# ============================================================================
class UserUpdate(UserBase):
    """
    更新用户请求模型（管理员使用）
    
    所有字段都是可选的，允许部分更新。
    
    与 UserBase 的区别：
    - 所有字段都可以为 None
    - email 可选（不需要每次都提供）
    - password 可选（不修改密码时不提供）
    
    使用场景：
    - PATCH /api/v1/users/{user_id} - 管理员更新用户
    
    注意：
    - 如果提供 password，会被哈希后更新
    - 如果不提供某字段，该字段保持不变
    """
    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    """
    用户更新自己信息的请求模型
    
    限制用户只能修改自己的基本信息，不能修改：
    - is_active（不能自己禁用自己）
    - is_superuser（不能自己提升权限）
    
    使用场景：
    - PATCH /api/v1/users/me - 用户更新自己的信息
    
    属性：
    - full_name: 修改用户名
    - email: 修改邮箱（需要验证邮箱唯一性）
    """
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    """
    修改密码请求模型
    
    需要提供当前密码进行验证，防止被盗号后修改密码。
    
    使用场景：
    - PATCH /api/v1/users/me/password - 用户修改密码
    
    验证流程：
    1. 验证 current_password 是否正确
    2. 对 new_password 进行哈希
    3. 更新数据库中的 hashed_password
    
    属性：
    - current_password: 当前密码（用于验证身份）
    - new_password: 新密码
    """
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# ============================================================================
# 数据库模型
# ============================================================================
class User(UserBase, table=True):
    """
    用户数据库模型
    
    映射到数据库表 "user"，存储用户账号信息。
    
    表结构：
    ┌────────────────┬─────────────┬──────────────────────────┐
    │ 字段名          │ 类型        │ 说明                      │
    ├────────────────┼─────────────┼──────────────────────────┤
    │ id             │ UUID        │ 主键                      │
    │ email          │ VARCHAR(255)│ 邮箱（唯一，索引）        │
    │ hashed_password│ VARCHAR     │ 密码哈希值                │
    │ is_active      │ BOOLEAN     │ 是否激活                  │
    │ is_superuser   │ BOOLEAN     │ 是否超级管理员            │
    │ full_name      │ VARCHAR(255)│ 用户全名                  │
    │ created_at     │ DATETIME    │ 创建时间                  │
    └────────────────┴─────────────┴──────────────────────────┘
    
    继承自 UserBase：
    - email
    - is_active
    - is_superuser
    - full_name
    
    新增字段：
    - id: UUID 主键
    - hashed_password: 密码哈希值（不是明文密码！）
    - created_at: 创建时间
    
    安全说明：
    - 永远不要存储明文密码
    - hashed_password 使用 bcrypt 算法
    - 密码验证使用 verify_password 函数
    """
    __tablename__ = "user"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_china,
        sa_type=DateTime(timezone=True),
    )


# ============================================================================
# 响应模型
# ============================================================================
class UserPublic(UserBase):
    """
    用户公开信息响应模型
    
    返回给前端的用户数据，不包含敏感信息。
    
    与 User 模型的区别：
    - 不包含 hashed_password（安全考虑）
    - 包含 id（前端需要）
    - 包含 created_at（显示注册时间）
    
    使用场景：
    - GET /api/v1/users/me - 获取当前用户信息
    - GET /api/v1/users/{user_id} - 获取指定用户信息
    - POST /api/v1/users/ - 创建用户后返回
    
    返回示例：
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "is_active": true,
        "is_superuser": false,
        "full_name": "张三",
        "created_at": "2024-01-15T10:30:00+08:00"
    }
    """
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    """
    用户列表响应模型
    
    用于分页返回多个用户，包含：
    - data: 用户列表
    - count: 总数量（用于前端分页）
    
    使用场景：
    - GET /api/v1/users/ - 获取用户列表
    
    返回示例：
    {
        "data": [
            {"id": "...", "email": "user1@example.com", ...},
            {"id": "...", "email": "user2@example.com", ...}
        ],
        "count": 100
    }
    """
    data: list[UserPublic]
    count: int
