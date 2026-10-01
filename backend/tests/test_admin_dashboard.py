import pytest
import jwt

from backend.app.config import settings
from backend.app.models.user import User
from backend.tests.test_devices import auth_headers, create_apartment_and_room, create_device


def test_assignment_updates_occupancy_including_shared_apartment(client, db_session, admin_user, tenant_user):
    first, _ = create_apartment_and_room(db_session, "First")
    second, _ = create_apartment_and_room(db_session, "Second")
    other = User(full_name="Other", email="other@example.com", password_hash="unused", apartment_id=first.id)
    db_session.add(other)
    db_session.commit()
    headers = auth_headers(admin_user)
    url = f"/users/{tenant_user.id}/apartment"
    assert client.put(url, headers=headers, json={"apartment_id": first.id}).status_code == 200
    assert first.status == "occupied"
    assert client.put(url, headers=headers, json={"apartment_id": second.id}).status_code == 200
    assert first.status == "occupied" and second.status == "occupied"
    assert client.delete(url, headers=headers).status_code == 200
    assert second.status == "available"
    assert client.delete(f"/users/{other.id}/apartment", headers=headers).status_code == 200
    assert first.status == "available"


def test_assignment_rejects_maintenance_and_inactive_tenants(client, db_session, admin_user, tenant_user):
    apartment, _ = create_apartment_and_room(db_session)
    apartment.status = "maintenance"
    db_session.commit()
    url = f"/users/{tenant_user.id}/apartment"
    headers = auth_headers(admin_user)
    assert client.put(url, headers=headers, json={"apartment_id": apartment.id}).status_code == 409
    apartment.status = "available"
    tenant_user.is_active = False
    db_session.commit()
    assert client.put(url, headers=headers, json={"apartment_id": apartment.id}).status_code == 409


def test_admin_deactivation_revokes_existing_token_and_reactivation_restores_access(client, admin_user, tenant_user):
    headers = auth_headers(admin_user)
    tenant_headers = auth_headers(tenant_user)
    url = f"/users/{tenant_user.id}/status"
    assert client.patch(url, headers=tenant_headers, json={"is_active": False}).status_code == 403
    assert client.patch(url, headers=headers, json={"is_active": False}).status_code == 200
    assert client.get("/users/me", headers=tenant_headers).status_code == 403
    assert client.post("/users/login", json={"email": tenant_user.email, "password": "StrongPassword123!"}).status_code == 403
    assert client.patch(url, headers=headers, json={"is_active": True}).status_code == 200
    profile = client.get("/users/me", headers=tenant_headers)
    assert profile.status_code == 200 and "password_hash" not in profile.json()
    assert client.patch(f"/users/{admin_user.id}/status", headers=headers, json={"is_active": False}).status_code == 409
    assert client.patch("/users/999/status", headers=headers, json={"is_active": True}).status_code == 404
    assert client.patch(url, headers=headers, json={"is_active": None}).status_code == 422


def test_tenant_status_and_dashboard_scope(client, db_session, admin_user, tenant_user):
    apartment, room = create_apartment_and_room(db_session)
    other_apartment, other_room = create_apartment_and_room(db_session, "Other")
    tenant_user.apartment_id = apartment.id
    create_device(db_session, room.id)
    create_device(db_session, other_room.id)
    db_session.commit()
    headers = auth_headers(admin_user)
    payload = {"tenant_id": tenant_user.id, "period": "2026-09", "due_date": "2000-01-01", "amount_minor": 100, "currency": "XAF"}
    assert client.post("/rent/", headers=headers, json=payload).status_code == 201
    assert client.post("/rent/", headers=headers, json={**payload, "period": "2026-10", "currency": "USD"}).status_code == 201
    tenant_headers = auth_headers(tenant_user)
    summary = client.get("/dashboard/summary", headers=tenant_headers).json()
    assert summary["apartments"] == 1 and summary["rooms"] == 1 and summary["devices"] == 1
    assert summary["rent_balances"] == [
        {"currency": "USD", "outstanding_minor": 100, "overdue_minor": 100},
        {"currency": "XAF", "outstanding_minor": 100, "overdue_minor": 100},
    ]
    all_summary = client.get("/dashboard/summary", headers=headers).json()
    assert all_summary["apartments"] == 2 and all_summary["devices"] == 2
    status = client.get(f"/users/{tenant_user.id}/tenant-status", headers=tenant_headers).json()
    assert status["tenancy_status"] == "assigned" and status["rent_balances"] == summary["rent_balances"]
    assert client.get(f"/users/{admin_user.id}/tenant-status", headers=tenant_headers).status_code == 403
    assert client.get("/users/999/tenant-status", headers=headers).status_code == 404
    tenant_user.apartment_id = None
    db_session.commit()
    empty = client.get("/dashboard/summary", headers=tenant_headers).json()
    assert empty["devices"] == 0 and empty["apartments"] == 0
    assert empty["rent_balances"] == summary["rent_balances"]


@pytest.mark.parametrize("subject", ["abc", "-1", "0", "9" * 100, "١"])
def test_malformed_signed_subject_returns_401(client, subject):
    token = jwt.encode({"sub": subject}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    assert client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_dashboard_requires_authentication_and_readiness(client):
    assert client.get("/dashboard/summary").status_code == 401
    assert client.get("/health/ready").json() == {"status": "ready"}
    schema = client.get("/openapi.json").json()
    for path in ("/dashboard/summary", "/rent/", "/apartments/{apartment_id}/automations/"):
        assert path in schema["paths"]


@pytest.mark.parametrize("resource,field", [("apartment", "floor"), ("room", "name"), ("device", "is_enabled")])
def test_admin_patch_rejects_null_required_fields(client, db_session, admin_user, resource, field):
    apartment, room = create_apartment_and_room(db_session)
    device = create_device(db_session, room.id)
    url = f"/apartments/{apartment.id}"
    if resource in ("room", "device"):
        url += f"/rooms/{room.id}"
    if resource == "device":
        url += f"/devices/{device.id}"
    assert client.patch(url, headers=auth_headers(admin_user), json={field: None}).status_code == 422
    assert client.get(url, headers=auth_headers(admin_user)).status_code == 200
