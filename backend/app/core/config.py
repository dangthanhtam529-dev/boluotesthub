"""
应用配置模块 (Application Configuration)

此模块使用 Pydantic Settings 管理应用的所有配置项。
配置值从环境变量或 .env 文件加载，支持类型验证和默认值。
"""

import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    MySQLDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    """
    解析 CORS 跨域配置
    
    支持两种格式：
    - 逗号分隔的字符串："http://localhost,http://localhost:5173"
    - JSON 数组字符串：'["http://localhost", "http://localhost:5173"]'
    """
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """
    应用配置类
    
    所有配置项都在这里定义，会自动从环境变量或 .env 文件加载。
    使用 Pydantic 进行类型验证，确保配置值符合预期。
    """
    
    # ============================================
    # Pydantic 配置
    # ============================================
    model_config = SettingsConfigDict(
        # 使用上级目录的 .env 文件（backend 的上一级）
        env_file="../.env",
        # 忽略空值的环境变量
        env_ignore_empty=True,
        # 忽略未定义的配置项（不报错）
        extra="ignore",
    )
    
    # ============================================
    # API 配置
    # ============================================
    # API 版本路径前缀
    API_V1_STR: str = "/api/v1"
    
    # JWT 安全密钥 - 用于签名和验证 token
    # 默认自动生成，但建议显式设置以确保重启后一致
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # JWT Token 过期时间（分钟）
    # 默认 8 天 = 60 分钟 × 24 小时 × 8 天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # ============================================
    # 前端配置
    # ============================================
    # 前端应用地址 - 用于生成邮件中的链接、CORS 配置等
    FRONTEND_HOST: str = "http://localhost:5173"
    
    # 运行环境：local(本地开发), staging(预发布), production(生产)
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # CORS 跨域配置 - 允许访问后端的域名列表
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """
        计算属性：获取所有允许的 CORS 来源
        
        合并 BACKEND_CORS_ORIGINS 和 FRONTEND_HOST
        用于 FastAPI CORS 中间件配置
        """
        origins = [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]
        origins.append(self.FRONTEND_HOST)
        # 确保包含 localhost 和 127.0.0.1 两种形式
        if "http://localhost:5173" not in origins:
            origins.append("http://localhost:5173")
        if "http://127.0.0.1:5173" not in origins:
            origins.append("http://127.0.0.1:5173")
        return origins

    # ============================================
    # 项目信息
    # ============================================
    # 项目名称 - 显示在 API 文档、邮件主题等位置
    PROJECT_NAME: str
    
    # Sentry DSN - 错误追踪和性能监控（可选）
    SENTRY_DSN: HttpUrl | None = None

    # ============================================
    # MySQL 数据库配置
    # ============================================
    # 数据库服务器地址
    MYSQL_SERVER: str
    # 数据库端口（MySQL 默认 3306）
    MYSQL_PORT: int = 3306
    # 数据库用户名
    MYSQL_USER: str
    # 数据库密码
    MYSQL_PASSWORD: str = ""
    # 数据库名称
    MYSQL_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> MySQLDsn:
        """
        计算属性：生成 SQLAlchemy 数据库连接 URI
        
        格式：mysql+pymysql://user:password@host:port/database?charset=utf8mb4
        
        注意：charset=utf8mb4 确保中文正确存储和读取
        """
        return MySQLDsn.build(
            scheme="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_SERVER,
            port=self.MYSQL_PORT,
            path=self.MYSQL_DB,
            query="charset=utf8mb4",
        )

    # ============================================
    # SMTP 邮件配置
    # ============================================
    # 启用 TLS 加密（推荐）
    SMTP_TLS: bool = True
    # 启用 SSL 加密（与 TLS 二选一）
    SMTP_SSL: bool = False
    # SMTP 端口（TLS 常用 587，SSL 常用 465）
    SMTP_PORT: int = 587
    # SMTP 服务器地址
    SMTP_HOST: str | None = None
    # SMTP 用户名
    SMTP_USER: str | None = None
    # SMTP 密码
    SMTP_PASSWORD: str | None = None
    # 发件人邮箱地址
    EMAILS_FROM_EMAIL: EmailStr | None = None
    # 发件人显示名称（默认使用项目名称）
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        """
        验证器：如果未设置发件人名称，默认使用项目名称
        """
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    # 密码重置令牌过期时间（小时）
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        """
        计算属性：检查邮件功能是否已启用
        
        需要配置 SMTP_HOST 和 EMAILS_FROM_EMAIL
        """
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    # ============================================
    # 用户配置
    # ============================================
    # 测试用户邮箱（用于测试邮件功能）
    EMAIL_TEST_USER: EmailStr = "test@example.com"
    # 第一个超级管理员邮箱（系统启动时自动创建）
    FIRST_SUPERUSER: EmailStr
    # 第一个超级管理员密码
    FIRST_SUPERUSER_PASSWORD: str

    # ============================================
    # Apifox 配置
    # ============================================
    # Apifox Access Token - 用于访问 Apifox API
    # 在 Apifox 网站生成：账号设置 -> API 访问令牌
    APIFOX_ACCESS_TOKEN: str | None = None
    # Apifox 项目 ID
    APIFOX_PROJECT_ID: str | None = None

    # ============================================
    # MongoDB 配置
    # ============================================
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "test_platform"

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """
        检查是否使用了默认的安全密钥
        
        如果是 "changethis"：
        - 本地环境：发出警告
        - 其他环境：抛出异常（阻止启动）
        """
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        """
        验证器：确保关键安全配置已修改默认值
        
        检查项：SECRET_KEY, MYSQL_PASSWORD, FIRST_SUPERUSER_PASSWORD
        """
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("MYSQL_PASSWORD", self.MYSQL_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


# 创建全局配置实例
# type: ignore 是因为 Pydantic 会在运行时验证，静态检查器无法识别
settings = Settings()  # type: ignore
