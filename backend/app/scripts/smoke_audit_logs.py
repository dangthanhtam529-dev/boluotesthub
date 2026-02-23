import logging

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine, init_db
from app.core.logging import setup_logging
from app.main import app
from app.models.audit_log import AuditLog


def main() -> int:
    setup_logging()
    logging.getLogger("app.smoke").info("smoke_start")

    with Session(engine) as session:
        init_db(session)
    AuditLog.__table__.create(bind=engine, checkfirst=True)

    client = TestClient(app)
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": settings.FIRST_SUPERUSER, "password": settings.FIRST_SUPERUSER_PASSWORD},
    )
    if r.status_code != 200:
        raise RuntimeError(f"login failed: {r.status_code} {r.text}")
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    item = client.post(
        f"{settings.API_V1_STR}/items/",
        headers=headers,
        json={"title": "smoke-audit", "description": "smoke"},
    )
    if item.status_code != 200:
        raise RuntimeError(f"create item failed: {item.status_code} {item.text}")
    item_id = item.json()["id"]

    logs = client.get(
        f"{settings.API_V1_STR}/audit-logs/?resource_type=item&resource_id={item_id}",
        headers=headers,
    )
    if logs.status_code != 200:
        raise RuntimeError(f"read audit logs failed: {logs.status_code} {logs.text}")
    payload = logs.json()
    if payload.get("count", 0) < 1:
        raise RuntimeError("no audit logs found")
    logging.getLogger("app.smoke").info("smoke_ok", extra={"audit_count": payload["count"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

