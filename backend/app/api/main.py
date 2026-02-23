from fastapi import APIRouter

from app.api.routes import audit_logs, items, login, private, users, utils
from app.api.routes.executions import router as executions_router
from app.api.routes.projects import router as projects_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.scheduled_tasks import router as scheduled_tasks_router
from app.api.routes.defects import router as defects_router
from app.api.routes.defect_import import router as defect_import_router
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(audit_logs.router)
api_router.include_router(executions_router)
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(notifications_router)
api_router.include_router(scheduled_tasks_router)
api_router.include_router(defects_router, prefix="/defects", tags=["defects"])
api_router.include_router(defect_import_router, prefix="/defects/import", tags=["defect-import"])


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
