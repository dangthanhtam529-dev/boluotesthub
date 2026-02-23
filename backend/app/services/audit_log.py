from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import Request
from sqlmodel import Session

from app.core.logging import get_request_id
from app.models.audit_log import AuditLog, AuditStatus
from app.models.user import User


SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "api_key",
    "secret",
    "client_secret",
}


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def _sanitize_value(value: Any, *, depth: int, max_depth: int) -> Any:
    if value is None:
        return None
    if depth >= max_depth:
        return "***"
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, str):
        return _truncate_text(value, 2000)
    if isinstance(value, list):
        return [_sanitize_value(v, depth=depth + 1, max_depth=max_depth) for v in value[:100]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            key_l = key.lower()
            if any(s in key_l for s in SENSITIVE_KEYS):
                out[key] = "***"
            else:
                out[key] = _sanitize_value(v, depth=depth + 1, max_depth=max_depth)
        return out
    try:
        return _truncate_text(str(value), 2000)
    except Exception:
        return "***"


def sanitize_payload(value: Any | None) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            value = value.model_dump()
        except Exception:
            value = str(value)
    if isinstance(value, dict):
        sanitized = _sanitize_value(value, depth=0, max_depth=5)
        if isinstance(sanitized, dict):
            try:
                raw = json.dumps(sanitized, ensure_ascii=False, default=str)
            except Exception:
                return {"_error": "payload_not_serializable"}
            if len(raw) > 20000:
                return {"_truncated": True}
            return sanitized
        return {"_error": "payload_invalid"}
    return {"value": _sanitize_value(value, depth=0, max_depth=5)}


def create_audit_log(
    *,
    session: Session,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    resource_name: str | None = None,
    status: AuditStatus | str = AuditStatus.SUCCESS,
    request: Request | None = None,
    actor: User | None = None,
    before: Any | None = None,
    after: Any | None = None,
    diff_summary: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> AuditLog:
    request_id = get_request_id()
    actor_user_id = getattr(actor, "id", None)
    actor_email = getattr(actor, "email", None)
    actor_ip = None
    user_agent = None
    if request is not None:
        actor_ip = getattr(getattr(request, "client", None), "host", None)
        user_agent = request.headers.get("user-agent")

    status_value = status.value if isinstance(status, AuditStatus) else str(status)
    log = AuditLog(
        request_id=request_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        actor_ip=actor_ip,
        user_agent=user_agent,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        before=sanitize_payload(before),
        after=sanitize_payload(after),
        diff_summary=_truncate_text(diff_summary, 1000) if diff_summary else None,
        status=status_value,
        error_code=error_code,
        error_message=_truncate_text(error_message, 8000) if error_message else None,
        duration_ms=duration_ms,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
