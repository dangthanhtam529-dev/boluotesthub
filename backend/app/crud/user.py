# 用户相关 CRUD 操作
from typing import Any
from sqlmodel import Session, select
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserCreate, UserUpdate


# 用于防止时序攻击的虚拟哈希值
# 这是一个随机密码的 Argon2 哈希，用于确保比较时间恒定
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def create_user(*, session: Session, user_create: UserCreate) -> User:
    """创建新用户"""
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    """更新用户信息"""
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    """通过邮箱获取用户"""
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def get_user_by_id(*, session: Session, user_id: str) -> User | None:
    """通过 ID 获取用户"""
    statement = select(User).where(User.id == user_id)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    """验证用户登录"""
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # 防止时序攻击：即使用户不存在也执行密码验证
        # 确保响应时间一致，防止通过时间差猜测邮箱是否存在
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    # 如果密码哈希已更新（迁移到新算法），保存新哈希
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user