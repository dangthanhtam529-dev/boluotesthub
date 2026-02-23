"""
MongoDB 连接管理模块 (MongoDB Connection Management)

本模块负责：
1. 管理 MongoDB 异步客户端的生命周期
2. 提供数据库实例的访问接口
3. 处理连接的安全日志（隐藏密码）

MongoDB 在项目中的用途：
┌─────────────────────────────────────────────────────────────┐
│                    MongoDB 数据库                            │
├─────────────────────────────────────────────────────────────┤
│  集合（Collections）：                                       │
│  ├── reports       - 测试报告完整数据                        │
│  │   └── 字段：execution_id, project_id, report_json, ...   │
│  ├── derived_data  - 派生数据（从报告提取）                  │
│  │   └── 字段：failures, errors, performance_metrics, ...   │
│  └── failure_fingerprints - 失败指纹（用于错误归类）        │
│       └── 字段：fingerprint, error_type, count, ...         │
├─────────────────────────────────────────────────────────────┤
│  为什么使用 MongoDB？                                        │
│  1. 报告数据量大且结构灵活（JSON 格式）                      │
│  2. 不需要复杂的关系查询                                     │
│  3. 支持高效的文档存储和聚合查询                             │
│  4. 与 MySQL 互补：MySQL 存结构化元数据，MongoDB 存报告数据  │
└─────────────────────────────────────────────────────────────┘

技术栈：
- Motor: MongoDB 的异步 Python 驱动
- AsyncIOMotorClient: 异步客户端，支持 async/await
"""

import logging
from urllib.parse import urlsplit, urlunsplit

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# ============================================================================
# 日志配置
# ============================================================================
# 使用专门的 logger 记录 MongoDB 相关日志
# 日志名称 "app.mongodb" 会在日志输出中显示，便于过滤和追踪
logger = logging.getLogger("app.mongodb")

# ============================================================================
# 全局变量
# ============================================================================
# MongoDB 客户端 - 全局单例，避免重复创建连接
# 类型提示：可能是 None（未初始化时）或 AsyncIOMotorClient
mongodb_client: AsyncIOMotorClient | None = None

# MongoDB 数据库实例 - 通过客户端获取
# 用于执行数据库操作（增删改查、聚合等）
mongodb_db = None


def _sanitize_mongodb_url(url: str) -> str:
    """
    清理 MongoDB URL 中的敏感信息（密码）
    
    用于日志输出，避免将密码明文写入日志文件。
    
    Args:
        url: 原始 MongoDB 连接 URL
             例如：mongodb://user:password@localhost:27017/database
    
    Returns:
        清理后的 URL（隐藏用户名和密码）
        例如：mongodb://localhost:27017/database
    
    示例：
        >>> _sanitize_mongodb_url("mongodb://admin:secret@localhost:27017/test")
        'mongodb://localhost:27017/test'
        
        >>> _sanitize_mongodb_url("mongodb://localhost:27017/test")
        'mongodb://localhost:27017/test'
    """
    try:
        # 解析 URL 为各个组成部分
        parts = urlsplit(url)
        
        # 如果包含用户名或密码，则移除
        if parts.username or parts.password:
            # 重建 netloc（网络位置），不包含认证信息
            netloc = parts.hostname or ""
            if parts.port:
                netloc = f"{netloc}:{parts.port}"
            
            # 重新组装 URL
            return urlunsplit((
                parts.scheme,    # 协议：mongodb
                netloc,          # 网络位置：host:port
                parts.path,      # 路径：/database
                parts.query,     # 查询参数
                parts.fragment,  # 片段
            ))
        return url
    except Exception:
        # 解析失败时返回安全占位符
        return "mongodb://***"


def init_mongodb() -> None:
    """
    初始化 MongoDB 连接
    
    此函数在应用启动时调用（见 main.py 的 startup_event）
    
    工作流程：
    1. 检查是否已初始化（避免重复创建连接）
    2. 创建异步 MongoDB 客户端
    3. 获取数据库实例
    4. 记录连接日志
    
    连接池说明：
    - Motor 客户端自动管理连接池
    - 默认最大连接数：100
    - 自动处理连接超时和重连
    
    注意：
    - 此函数是同步的，但客户端本身支持异步操作
    - 实际的数据库操作使用 async/await
    
    全局变量修改：
    - mongodb_client: 设置为 AsyncIOMotorClient 实例
    - mongodb_db: 设置为数据库实例
    """
    global mongodb_client, mongodb_db
    
    # 避免重复初始化
    if mongodb_client is not None and mongodb_db is not None:
        return

    # 创建异步 MongoDB 客户端
    # AsyncIOMotorClient 特性：
    # - 支持异步操作（async/await）
    # - 自动连接池管理
    # - 自动重连机制
    mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
    
    # 获取数据库实例
    # 数据库实例用于执行具体的数据库操作
    # 例如：mongodb_db.reports.insert_one({...})
    mongodb_db = mongodb_client[settings.MONGODB_DB_NAME]
    
    # 记录连接成功日志
    # 注意：使用 _sanitize_mongodb_url 隐藏密码
    logger.info(
        "mongodb_connected",
        extra={
            "mongodb_url": _sanitize_mongodb_url(settings.MONGODB_URL),
            "mongodb_db": settings.MONGODB_DB_NAME,
        },
    )


def get_mongodb_db():
    """
    获取 MongoDB 数据库实例
    
    用于在服务层或 API 层访问数据库
    
    Returns:
        MongoDB 数据库实例，用于执行数据库操作
    
    使用示例：
        # 在服务层中使用
        db = get_mongodb_db()
        collection = db.reports
        await collection.insert_one({"execution_id": "xxx", ...})
        
        # 聚合查询
        pipeline = [
            {"$match": {"project_id": "project_123"}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        result = await db.reports.aggregate(pipeline).to_list(None)
    
    注意：
    - 返回 None 表示 MongoDB 未初始化
    - 调用此函数前应确保 init_mongodb() 已执行
    """
    return mongodb_db


def get_mongodb_client():
    """
    获取 MongoDB 客户端实例
    
    用于需要客户端级别操作的场景，例如：
    - 列出所有数据库
    - 执行管理命令
    - 关闭连接
    
    Returns:
        AsyncIOMotorClient 实例
    
    使用示例：
        client = get_mongodb_client()
        
        # 列出所有数据库
        db_names = await client.list_database_names()
        
        # 执行管理命令
        result = await client.admin.command("ping")
    """
    return mongodb_client


async def close_mongodb() -> None:
    """
    关闭 MongoDB 连接
    
    此函数在应用关闭时调用（见 main.py 的 shutdown_event）
    
    工作流程：
    1. 检查客户端是否存在
    2. 关闭客户端连接
    3. 记录关闭日志
    
    注意：
    - 必须是异步函数（async），因为 Motor 客户端的 close 是异步的
    - 关闭连接会释放所有连接池中的连接
    - 未完成的操作会被取消
    
    资源清理：
    - 关闭所有打开的连接
    - 清理连接池
    - 释放相关资源
    """
    if mongodb_client:
        mongodb_client.close()
        logger.info("mongodb_connection_closed")
