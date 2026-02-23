from fastapi.testclient import TestClient

from app.core.config import settings


def test_audit_logs_requires_superuser(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/audit-logs/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_audit_logs_created_on_item_create(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"title": "Audit Item", "description": "Audit"}
    resp = client.post(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        json=data,
    )
    assert resp.status_code == 200
    item_id = resp.json()["id"]

    logs = client.get(
        f"{settings.API_V1_STR}/audit-logs/?resource_type=item&resource_id={item_id}",
        headers=superuser_token_headers,
    )
    assert logs.status_code == 200
    payload = logs.json()
    assert payload["count"] >= 1
    assert any(r["action"] == "create" and r["resource_type"] == "item" for r in payload["data"])

