import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.crud.audit_log import count_audit_logs, get_audit_log, get_audit_logs
from app.models.audit_log import AuditLogPublic, AuditLogsPublic


router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=AuditLogsPublic,
)
def read_audit_logs(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 50,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> Any:
    logs = get_audit_logs(
        session=session,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        q=q,
    )
    count = count_audit_logs(
        session=session,
        start_date=start_date,
        end_date=end_date,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        q=q,
    )
    return AuditLogsPublic(data=logs, count=count)


@router.get(
    "/{audit_log_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=AuditLogPublic,
)
def read_audit_log(
    session: SessionDep, current_user: CurrentUser, audit_log_id: uuid.UUID
) -> Any:
    log = get_audit_log(session=session, audit_log_id=audit_log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log

