"""
数据库连接和初始化模块 (Database Connection & Initialization)

本模块负责：
1. 创建 SQLAlchemy/SQLModel 数据库引擎
2. 初始化数据库（创建超级管理员用户）

数据库架构说明：
┌─────────────────────────────────────────────────────────────┐
│                    MySQL 数据库                              │
├─────────────────────────────────────────────────────────────┤
│  表结构：                                                    │
│  ├── user          - 用户表（登录、权限）                    │
│  ├── item          - 示例项目表（可删除）                    │
│  ├── project       - 项目表                                  │
│  ├── collection    - 测试集合表                              │
│  ├── testexecution - 测试执行记录表                          │
│  └── auditlog      - 审计日志表                              │
├─────────────────────────────────────────────────────────────┤
│  关系：                                                      │
│  User 1:N Project     (用户拥有多个项目)                     │
│  Project 1:N Collection  (项目包含多个测试集合)              │
│  Project 1:N TestExecution (项目有多个执行记录)              │
└─────────────────────────────────────────────────────────────┘

注意：表结构通过 Alembic 迁移管理，不是自动创建
"""

from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models.user import User, UserCreate

# ============================================================================
# 数据库引擎创建
# ============================================================================
# create_engine 创建数据库连接池引擎
# 连接 URI 格式：mysql+pymysql://user:password@host:port/database
# 
# 引擎特性：
# - 自动管理连接池
# - 支持连接复用
# - 处理连接超时和重连
#
# 使用方式：
# - 依赖注入：通过 get_db() 获取 Session
# - 直接使用：Session(engine) 创建会话
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# ============================================================================
# 重要提示：模型导入顺序
# ============================================================================
# 确保所有 SQLModel 模型在初始化数据库之前已导入
# 否则 SQLModel 可能无法正确初始化模型之间的关系
# 
# 例如，如果 User 模型引用了 Project 模型，但 Project 还未导入，
# 关系定义可能会失败。
#
# 更多详情：https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    """
    初始化数据库
    
    此函数在应用启动时调用（见 backend_pre_start.py 和 initial_data.py）
    
    主要工作：
    1. 检查是否已存在超级管理员用户
    2. 如果不存在，根据配置创建第一个超级管理员
    
    注意：
    - 表结构应该通过 Alembic 迁移创建，而不是自动创建
    - 如果不想使用迁移，可以取消下面的注释来自动创建表
    - 但不推荐这样做，因为无法追踪数据库变更
    
    Args:
        session: SQLModel 数据库会话
        
    数据流程：
    1. 查询 user 表中是否存在配置的超级管理员邮箱
    2. 如果不存在，创建新的超级管理员用户
    3. 密码会自动进行哈希处理（见 crud.create_user）
    
    示例：
        # 在 backend_pre_start.py 中调用
        with Session(engine) as session:
            init_db(session)
    """
    # ============================================================================
    # 表创建说明
    # ============================================================================
    # 表应该通过 Alembic 迁移创建，这样可以：
    # 1. 追踪数据库结构变更
    # 2. 支持版本回滚
    # 3. 团队协作时保持数据库一致
    #
    # 如果不想使用迁移，可以取消下面的注释来自动创建表：
    # from sqlmodel import SQLModel
    # SQLModel.metadata.create_all(engine)
    #
    # 但这会跳过迁移系统，不推荐在生产环境使用

    # ============================================================================
    # 创建超级管理员
    # ============================================================================
    # 检查配置的超级管理员邮箱是否已存在
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    
    # 如果不存在，创建新的超级管理员
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,           # 从配置读取邮箱
            password=settings.FIRST_SUPERUSER_PASSWORD,  # 从配置读取密码
            is_superuser=True,                        # 设置为超级管理员
        )
        # crud.create_user 会：
        # 1. 对密码进行哈希处理
        # 2. 创建用户记录
        # 3. 返回用户对象
        user = crud.create_user(session=session, user_create=user_in)
