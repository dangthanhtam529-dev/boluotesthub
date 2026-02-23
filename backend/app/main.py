"""
FastAPI 应用入口文件

本文件是整个后端服务的启动入口，负责：
1. 创建 FastAPI 应用实例
2. 配置中间件（CORS、请求上下文）
3. 注册路由
4. 管理应用生命周期（启动/关闭时的资源初始化和清理）

启动方式：
- 开发环境：uvicorn app.main:app --reload
- 生产环境：通过 gunicorn + uvicorn worker

架构说明：
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                          │
├─────────────────────────────────────────────────────────────┤
│  Middleware Stack (中间件栈，按添加顺序逆序执行)              │
│  ├── RequestContextMiddleware (请求上下文，生成 request_id)  │
│  └── CORSMiddleware (跨域处理)                              │
├─────────────────────────────────────────────────────────────┤
│  Routers (路由层)                                           │
│  ├── /api/v1/auth     → 登录认证                            │
│  ├── /api/v1/users    → 用户管理                            │
│  ├── /api/v1/projects → 项目管理                            │
│  ├── /api/v1/executions → 测试执行                          │
│  └── ...                                                    │
├─────────────────────────────────────────────────────────────┤
│  Services (服务层)                                          │
│  ├── ApifoxService (Apifox CLI 集成)                        │
│  ├── MongoDBReportService (报告存储)                        │
│  └── AuditLogService (审计日志)                             │
├─────────────────────────────────────────────────────────────┤
│  Data Layer (数据层)                                        │
│  ├── MySQL (SQLModel) → 用户、项目、执行记录                 │
│  └── MongoDB (Motor) → 测试报告、派生数据                    │
└─────────────────────────────────────────────────────────────┘
"""

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.logging import RequestContextMiddleware, setup_logging
from app.core.mongodb import init_mongodb, close_mongodb
from app.services.mongodb_report import MongoDBReportService

# ============================================================================
# 日志初始化
# ============================================================================
# 在应用启动最开始就配置日志系统，确保后续所有日志都能正确格式化
# setup_logging() 会：
# 1. 配置日志格式（包含 request_id、user_id 等上下文信息）
# 2. 设置日志级别（根据环境变量）
# 3. 配置日志输出目标（控制台、文件等）
setup_logging()


# ============================================================================
# OpenAPI 文档配置
# ============================================================================
def custom_generate_unique_id(route: APIRoute) -> str:
    """
    为 OpenAPI 文档中的每个 API 端点生成唯一 ID
    
    默认情况下，FastAPI 使用函数名作为 ID，这可能导致重复。
    我们自定义格式为：{标签}-{函数名}，例如：users-get_users
    
    这个 ID 用于：
    1. OpenAPI 文档中的 operationId
    2. 前端代码生成时的函数名
    
    Args:
        route: FastAPI 路由对象，包含路径、方法、标签等信息
        
    Returns:
        str: 格式化的唯一 ID，如 "users-list_users"
    
    示例：
        GET /api/v1/users/ → "users-list_users"
        POST /api/v1/projects/ → "projects-create_project"
    """
    return f"{route.tags[0]}-{route.name}"


# ============================================================================
# Sentry 错误监控初始化
# ============================================================================
# Sentry 是一个错误追踪和性能监控平台
# 只在生产环境且配置了 DSN 时才启用
if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),  # Sentry 项目 DSN
        enable_tracing=True,            # 启用性能追踪
    )

# ============================================================================
# FastAPI 应用实例创建
# ============================================================================
app = FastAPI(
    title=settings.PROJECT_NAME,                              # API 文档标题
    openapi_url=f"{settings.API_V1_STR}/openapi.json",        # OpenAPI schema 地址
    generate_unique_id_function=custom_generate_unique_id,    # 自定义 ID 生成函数
)

# ============================================================================
# 中间件配置
# ============================================================================
# 中间件执行顺序：后添加的先执行（栈结构）
# 请求流向：Request → CORSMiddleware → RequestContextMiddleware → Route Handler

# 1. 请求上下文中间件
# 为每个请求生成唯一的 request_id，用于日志追踪和问题定位
# 在日志中可以看到类似：request_id=abc123 user_id=user456
app.add_middleware(RequestContextMiddleware)

# 2. CORS 跨域中间件
# 允许前端（不同域名/端口）访问后端 API
# 开发环境：前端 localhost:5173 访问后端 localhost:8000
# 生产环境：可能需要限制 allow_origins 为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,  # 从配置读取允许的来源
    allow_credentials=True,        # 允许携带 Cookie
    allow_methods=["*"],           # 允许所有 HTTP 方法
    allow_headers=["*"],           # 允许所有请求头
)

# ============================================================================
# 路由注册
# ============================================================================
# api_router 包含了所有业务路由的定义
# 所有 API 都以 /api/v1 为前缀，例如：
# - /api/v1/auth/login
# - /api/v1/users/
# - /api/v1/projects/
app.include_router(api_router, prefix=settings.API_V1_STR)


# ============================================================================
# 应用生命周期事件
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行的初始化逻辑
    
    执行顺序：
    1. init_mongodb() - 初始化 MongoDB 连接池
    2. ensure_indexes() - 确保必要的索引已创建
    3. init_scheduler() - 初始化定时任务调度器并恢复任务
    
    MongoDB 索引说明：
    - reports 集合：project_id, execution_id, created_at 等字段索引
    - 索引用于加速查询，避免全表扫描
    
    注意：
    - 这里使用 try-except 是因为索引创建失败不应阻止应用启动
    - 在生产环境中，索引通常通过迁移脚本预先创建
    """
    init_mongodb()
    try:
        await MongoDBReportService.ensure_indexes()
    except Exception:
        import logging
        logging.getLogger("app.startup").exception("mongodb_indexes_init_failed")
    
    from app.services.scheduler_service import scheduler_service, restore_scheduled_tasks
    scheduler_service.start()
    restore_scheduled_tasks()


@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时执行的清理逻辑
    
    主要工作：
    1. 关闭定时任务调度器
    2. 关闭 MongoDB 连接池，释放资源
    
    注意：
    - 使用 async 函数确保异步资源正确释放
    - MySQL 连接由 SQLModel/SQLAlchemy 自动管理
    """
    from app.services.scheduler_service import scheduler_service
    scheduler_service.shutdown(wait=False)
    
    await close_mongodb()


# ============================================================================
# 开发环境直接运行入口
# ============================================================================
# 当直接运行此文件时（python -m app.main），启动开发服务器
# 生产环境通常使用 gunicorn + uvicorn worker 方式启动
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",    # 监听所有网络接口
        port=8000,          # 端口号
        reload=True,        # 代码变更自动重载（开发模式）
    )
