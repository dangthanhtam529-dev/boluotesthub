"""
API 依赖注入模块 (API Dependencies)

本模块定义了 FastAPI 路由中使用的依赖项（Dependencies）。
依赖注入是 FastAPI 的核心特性，用于：
1. 数据库会话管理
2. 用户认证和授权
3. 请求上下文设置

依赖注入流程图：
┌─────────────────────────────────────────────────────────────┐
│                    HTTP 请求                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  OAuth2PasswordBearer (提取 Token)                          │
│  从 Authorization header 提取 Bearer token                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  get_db() (数据库会话)                                       │
│  创建数据库会话，请求结束后自动关闭                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  get_current_user() (用户认证)                               │
│  解析 JWT token，验证用户身份                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  路由处理函数                                                │
│  接收已验证的用户和数据库会话                                │
└─────────────────────────────────────────────────────────────┘

使用方式：
    @router.get("/users/me")
    def get_current_user_info(current_user: CurrentUser):
        return current_user
"""

from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.logging import set_user_id
from app.models.user import User
from app.models import TokenPayload

# ============================================================================
# OAuth2 认证方案
# ============================================================================
# OAuth2PasswordBearer 是 FastAPI 内置的认证方案
# 它会：
# 1. 从请求头 Authorization 中提取 Bearer token
# 2. 如果没有 token，返回 401 Unauthorized
# 3. tokenUrl 指定了获取 token 的端点（用于 OpenAPI 文档）
#
# 请求格式：
# Authorization: Bearer <token>
#
# tokenUrl 告诉客户端去哪里获取 token（登录接口）
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


# ============================================================================
# 数据库会话依赖
# ============================================================================
def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    
    这是一个生成器函数，用于管理数据库会话的生命周期：
    1. 创建新的数据库会话
    2. yield 会话给路由处理函数
    3. 请求结束后自动关闭会话
    
    使用 with 语句确保会话正确关闭，即使发生异常。
    
    Yields:
        Session: SQLModel 数据库会话
    
    使用示例：
        @router.get("/items/")
        def get_items(session: SessionDep):
            items = session.exec(select(Item)).all()
            return items
    
    注意：
    - 每个请求获得独立的会话
    - 会话在请求结束后自动关闭
    - 使用连接池管理数据库连接
    """
    with Session(engine) as session:
        yield session


# ============================================================================
# 类型别名定义
# ============================================================================
# 使用 Annotated 创建可复用的依赖类型
# 这样在路由函数中可以直接使用类型注解，代码更简洁

# SessionDep: 数据库会话依赖
# 用法：def my_route(session: SessionDep):
SessionDep = Annotated[Session, Depends(get_db)]

# TokenDep: Token 依赖
# 用法：def my_route(token: TokenDep):
TokenDep = Annotated[str, Depends(reusable_oauth2)]


# ============================================================================
# 用户认证依赖
# ============================================================================
def get_current_user(session: SessionDep, token: TokenDep) -> User:
    """
    获取当前登录用户
    
    这是核心的认证函数，用于验证 JWT token 并返回用户对象。
    
    认证流程：
    1. 解码 JWT token
    2. 验证 token 格式和签名
    3. 从 token 中提取用户 ID
    4. 从数据库查询用户
    5. 验证用户状态（是否激活）
    6. 设置日志上下文（user_id）
    
    Args:
        session: 数据库会话（自动注入）
        token: JWT token 字符串（自动注入）
    
    Returns:
        User: 当前登录的用户对象
    
    Raises:
        HTTPException: 
            - 403: token 无效或过期
            - 404: 用户不存在
            - 400: 用户已禁用
    
    错误处理：
    - InvalidTokenError: JWT 解码失败（签名错误、过期等）
    - ValidationError: token payload 格式不正确
    - ValueError: 用户 ID 格式不正确
    
    日志上下文：
    - 调用 set_user_id() 设置当前用户 ID
    - 后续日志会自动包含 user_id 字段
    """
    try:
        # 解码 JWT token
        # jwt.decode 会验证：
        # - 签名是否正确（使用 SECRET_KEY）
        # - token 是否过期（exp 声明）
        # - 算法是否匹配
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[security.ALGORITHM]
        )
        
        # 将 payload 解析为 TokenPayload 对象
        # 这会验证 payload 结构是否符合预期
        token_data = TokenPayload(**payload)
        
    except (InvalidTokenError, ValidationError):
        # token 无效：签名错误、过期、格式错误等
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # 将字符串 ID 转换为 UUID 对象
    # token 中的 sub（subject）是用户 ID 的字符串形式
    import uuid
    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid user ID format")
    
    # 从数据库查询用户
    # session.get() 通过主键查询，效率最高
    user = session.get(User, user_id)
    
    # 用户不存在
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 用户已禁用
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # 设置日志上下文中的用户 ID
    # 后续所有日志都会包含 user_id 字段，便于追踪
    set_user_id(str(user.id))
    
    return user


# CurrentUser: 当前用户依赖
# 用法：def my_route(current_user: CurrentUser):
CurrentUser = Annotated[User, Depends(get_current_user)]


# ============================================================================
# 用户授权依赖
# ============================================================================
def get_current_active_user(current_user: CurrentUser) -> User:
    """
    获取当前活跃用户
    
    验证用户是否处于活跃状态。
    这是一个额外的安全检查，确保只有活跃用户可以访问。
    
    Args:
        current_user: 当前用户（已通过 get_current_user 验证）
    
    Returns:
        User: 当前活跃用户
    
    Raises:
        HTTPException: 400 - 用户已禁用
    
    注意：
    - get_current_user 已经检查了 is_active
    - 这个函数主要用于需要明确区分"活跃用户"的场景
    - 可以作为额外的安全层
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(current_user: CurrentUser) -> User:
    """
    获取当前超级管理员用户
    
    验证当前用户是否为超级管理员。
    用于保护需要管理员权限的接口。
    
    Args:
        current_user: 当前用户（已通过 get_current_user 验证）
    
    Returns:
        User: 当前超级管理员用户
    
    Raises:
        HTTPException: 403 - 权限不足
    
    使用示例：
        @router.delete("/users/{user_id}")
        def delete_user(
            user_id: UUID,
            current_user: CurrentUser = Depends(get_current_active_superuser)
        ):
            # 只有超级管理员可以删除用户
            ...
    
    权限层级：
    1. 普通用户：可以访问自己的数据
    2. 超级管理员：可以访问所有数据和功能
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, 
            detail="The user doesn't have enough privileges"
        )
    return current_user
