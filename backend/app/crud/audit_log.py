import uuid
from datetime import datetime

from sqlmodel import Session, col, func, select

from app.models.audit_log import AuditLog


def get_audit_logs(
    *,
    session: Session,
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
) -> list[AuditLog]:
    statement = select(AuditLog)
    if start_date:
        statement = statement.where(AuditLog.created_at >= start_date)
    if end_date:
        statement = statement.where(AuditLog.created_at <= end_date)
    if actor_user_id:
        statement = statement.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if resource_type:
        statement = statement.where(AuditLog.resource_type == resource_type)
    if resource_id:
        statement = statement.where(AuditLog.resource_id == resource_id)
    if status:
        statement = statement.where(AuditLog.status == status)
    if q:
        like = f"%{q}%"
        statement = statement.where(
            (AuditLog.resource_name.ilike(like))
            | (AuditLog.resource_id.ilike(like))
            | (AuditLog.error_message.ilike(like))
            | (AuditLog.actor_email.ilike(like))
        )
    statement = statement.order_by(col(AuditLog.created_at).desc()).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def count_audit_logs(
    *,
    session: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> int:
    statement = select(func.count()).select_from(AuditLog)
    if start_date:
        statement = statement.where(AuditLog.created_at >= start_date)
    if end_date:
        statement = statement.where(AuditLog.created_at <= end_date)
    if actor_user_id:
        statement = statement.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if resource_type:
        statement = statement.where(AuditLog.resource_type == resource_type)
    if resource_id:
        statement = statement.where(AuditLog.resource_id == resource_id)
    if status:
        statement = statement.where(AuditLog.status == status)
    if q:
        like = f"%{q}%"
        statement = statement.where(
            (AuditLog.resource_name.ilike(like))
            | (AuditLog.resource_id.ilike(like))
            | (AuditLog.error_message.ilike(like))
            | (AuditLog.actor_email.ilike(like))
        )
    return session.exec(statement).one()


def get_audit_log(*, session: Session, audit_log_id: uuid.UUID) -> AuditLog | None:
    return session.get(AuditLog, audit_log_id)

