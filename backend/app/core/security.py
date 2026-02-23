"""
安全模块 (Security Module)

本模块提供认证和密码安全相关的功能：
1. JWT Token 生成和验证
2. 密码哈希和验证
3. 密码哈希算法升级支持

安全架构：
┌─────────────────────────────────────────────────────────────┐
│                    用户认证流程                              │
├─────────────────────────────────────────────────────────────┤
│  1. 用户登录                                                 │
│     POST /api/v1/login/access-token                         │
│     { "username": "email", "password": "xxx" }              │
├─────────────────────────────────────────────────────────────┤
│  2. 密码验证                                                 │
│     verify_password(plain_password, hashed_password)        │
│     - 从数据库获取 hashed_password                           │
│     - 验证明文密码是否匹配                                   │
├─────────────────────────────────────────────────────────────┤
│  3. 生成 JWT Token                                          │
│     create_access_token(user_id, expires_delta)             │
│     - 设置过期时间                                           │
│     - 使用 SECRET_KEY 签名                                   │
│     - 返回 token 字符串                                      │
├─────────────────────────────────────────────────────────────┤
│  4. 返回 Token                                              │
│     { "access_token": "xxx", "token_type": "bearer" }       │
└─────────────────────────────────────────────────────────────┘

密码安全策略：
- 使用 Argon2 和 bcrypt 双算法支持
- Argon2 是推荐的现代密码哈希算法（抗 GPU 攻击）
- bcrypt 是广泛使用的传统算法（向后兼容）
- 支持自动升级旧哈希到新算法
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# ============================================================================
# 密码哈希配置
# ============================================================================
# PasswordHash 是 pwdlib 库的核心类，支持多种哈希算法
# 配置了两个哈希器：
# 1. Argon2Hasher - 首选算法，现代密码哈希竞赛冠军
# 2. BcryptHasher - 兼容算法，支持验证旧的 bcrypt 哈希
#
# 工作原理：
# - 新密码使用第一个算法（Argon2）哈希
# - 验证时自动检测哈希类型并使用对应算法
# - 如果检测到旧算法哈希，可以自动升级
#
# Argon2 优势：
# - 抗 GPU/ASIC 攻击
# - 内存密集型，难以并行破解
# - 可配置时间/内存成本
#
# Bcrypt 优势：
# - 广泛支持，兼容性好
# - 自带盐值
# - 计算成本可调
password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)


# ============================================================================
# JWT 配置
# ============================================================================
# JWT 签名算法
# HS256 = HMAC SHA-256
# 对称加密，使用同一个 SECRET_KEY 进行签名和验证
#
# 其他可选算法：
# - HS384, HS512: 更长的哈希
# - RS256, RS384, RS512: 非对称加密（需要公钥/私钥）
#
# 选择 HS256 的原因：
# - 性能好（对称加密更快）
# - 实现简单（只需要一个密钥）
# - 安全性足够（256位哈希）
ALGORITHM = "HS256"


# ============================================================================
# JWT Token 函数
# ============================================================================
def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    """
    创建 JWT 访问令牌
    
    JWT (JSON Web Token) 是一种开放标准 (RFC 7519)，
    用于在各方之间安全地传输信息作为 JSON 对象。
    
    Token 结构：
    ┌─────────────────────────────────────────────────────────┐
    │  Header.Payload.Signature                                │
    │                                                          │
    │  Header (Base64):                                        │
    │  { "alg": "HS256", "typ": "JWT" }                       │
    │                                                          │
    │  Payload (Base64):                                       │
    │  { "sub": "user_id", "exp": 1234567890 }                │
    │                                                          │
    │  Signature:                                              │
    │  HMACSHA256(base64(header) + "." + base64(payload),    │
    │             secret_key)                                  │
    └─────────────────────────────────────────────────────────┘
    
    Args:
        subject: Token 主体，通常是用户 ID
        expires_delta: 过期时间间隔
    
    Returns:
        str: 编码后的 JWT token 字符串
    
    示例：
        token = create_access_token(
            subject="550e8400-e29b-41d4-a716-446655440000",
            expires_delta=timedelta(hours=8)
        )
        # 返回类似：eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    
    安全考虑：
    - exp 声明确保 token 会过期
    - sub 声明标识用户身份
    - 使用 SECRET_KEY 签名防止篡改
    - 不要在 payload 中存储敏感信息（Base64 不是加密）
    """
    # 计算过期时间
    # 使用 UTC 时间避免时区问题
    expire = datetime.now(timezone.utc) + expires_delta
    
    # 构建 payload
    # sub (subject): Token 主体，通常是用户 ID
    # exp (expiration): 过期时间戳
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # 编码 JWT
    # jwt.encode 会：
    # 1. 创建 header（算法和类型）
    # 2. 序列化 payload
    # 3. 使用 SECRET_KEY 签名
    # 4. 返回完整的 token 字符串
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


# ============================================================================
# 密码函数
# ============================================================================
def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    """
    验证密码
    
    检查明文密码是否与哈希值匹配。
    
    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的哈希值
    
    Returns:
        tuple[bool, str | None]:
            - bool: 验证结果（True = 匹配）
            - str | None: 如果需要升级哈希，返回新的哈希值；否则 None
    
    使用示例：
        is_valid, new_hash = verify_password("user_input", stored_hash)
        if is_valid:
            if new_hash:
                # 哈希算法已升级，更新数据库
                user.hashed_password = new_hash
            # 登录成功
        else:
            # 密码错误
    
    哈希升级场景：
        1. 用户使用旧算法（bcrypt）哈希的密码登录
        2. 验证成功后，返回新的 Argon2 哈希
        3. 系统自动更新数据库中的哈希值
        4. 下次登录使用新算法验证
    
    安全考虑：
        - 使用恒定时间比较（防止时序攻击）
        - 自动处理盐值（每个哈希有唯一盐）
        - 支持算法迁移（平滑升级）
    """
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    使用配置的首选算法（Argon2）对密码进行哈希。
    
    Args:
        password: 明文密码
    
    Returns:
        str: 哈希后的密码字符串
    
    示例：
        >>> get_password_hash("my_password")
        '$argon2id$v=19$m=65536,t=3,p=4$...'
    
    哈希格式说明：
        Argon2 格式：
        $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
        
        - argon2id: 算法版本
        - v=19: 版本号
        - m=65536: 内存成本（KB）
        - t=3: 时间成本（迭代次数）
        - p=4: 并行度
        - salt: 随机盐值
        - hash: 最终哈希值
    
    Bcrypt 格式：
        $2b$12$<22字符盐><31字符哈希>
        
        - 2b: 算法版本
        - 12: 成本因子（2^12 轮）
        - 盐和哈希：Base64 编码
    
    安全考虑：
        - 每次调用生成不同的哈希（随机盐）
        - 哈希过程故意缓慢（增加破解成本）
        - 哈希值包含算法信息（便于未来迁移）
    """
    return password_hash.hash(password)
