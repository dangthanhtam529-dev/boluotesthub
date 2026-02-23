# 兼容层：从新的模块重新导出所有 CRUD 操作
# 注意：新代码建议直接从 app.crud.xxx 导入

# 用户 CRUD
from app.crud.user import (
    create_user,
    update_user,
    get_user_by_email,
    authenticate,
)

# 项目 CRUD
from app.crud.item import create_item

# 测试执行 CRUD
from app.crud.execution import (
    create_execution,
    get_execution,
    get_executions,
    update_execution,
    delete_execution,
    get_execution_stats,
)

__all__ = [
    # 用户
    "create_user",
    "update_user",
    "get_user_by_email",
    "authenticate",
    # 项目
    "create_item",
    # 测试执行
    "create_execution",
    "get_execution",
    "get_executions",
    "update_execution",
    "delete_execution",
    "get_execution_stats",
]