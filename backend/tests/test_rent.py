from datetime import datetime, timedelta, timezone
import pytest

from backend.app.models.user import User
from backend.tests.test_devices import auth_headers, create_apartment_and_room


@pytest.fixture
def rent_setup(db_session, tenant_user):
    apartment, _ = create_apartment_and_room(db_session)
    tenant_user.apartment_id = apartment.id
    db_session.commit()
    return apartment, {
        "tenant_id": tenant_user.id, "period": "2026-09",
        "due_date": (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat(),
        "amount_minor": 100000, "currency": "XAF",
    }


def create_charge(client, admin_user, payload):
    result = client.post("/rent/", headers=auth_headers(admin_user), json=payload)
    assert result.status_code == 201, result.text
    return result.json()


def test_rent_payment_lifecycle(client, admin_user, tenant_user, rent_setup):
    _, payload = rent_setup
    charge = create_charge(client, admin_user, payload)
    assert charge["status"] == "unpaid"
    payment_url = f"/rent/{charge['id']}/payment"
    headers = auth_headers(admin_user)
    partial = client.put(payment_url, headers=headers, json={"paid_amount_minor": 20000}).json()
    assert partial["status"] == "partial"
    assert partial["balance_minor"] == 80000
    paid = client.put(payment_url, headers=headers, json={"paid_amount_minor": 100000}).json()
    assert paid["status"] == "paid" and paid["paid_at"]
    repeated = client.put(payment_url, headers=headers, json={"paid_amount_minor": 100000}).json()
    assert repeated == paid
    assert client.get(f"/rent/{charge['id']}", headers=auth_headers(tenant_user)).json() == paid
    corrected = client.put(payment_url, headers=headers, json={"paid_amount_minor": 0}).json()
    assert corrected["status"] == "unpaid" and corrected["paid_at"] is None


def test_overdue_and_duplicate_charge(client, admin_user, rent_setup):
    _, payload = rent_setup
    payload["due_date"] = "2000-01-01"
    charge = create_charge(client, admin_user, payload)
    assert charge["status"] == "overdue"
    assert client.post("/rent/", headers=auth_headers(admin_user), json=payload).status_code == 409
    result = client.put(f"/rent/{charge['id']}/payment", headers=auth_headers(admin_user), json={"paid_amount_minor": 100000})
    assert result.json()["status"] == "paid"


@pytest.mark.parametrize("key,value", [("amount_minor", 0), ("amount_minor", -1), ("amount_minor", 10.5), ("amount_minor", True), ("currency", "xaf"), ("period", "2026-13"), ("due_date", "invalid")])
def test_rent_validation(client, admin_user, rent_setup, key, value):
    _, payload = rent_setup
    assert client.post("/rent/", headers=auth_headers(admin_user), json={**payload, key: value}).status_code == 422


@pytest.mark.parametrize("amount", [-1, 100001, 1.5, True])
def test_invalid_payment_leaves_charge_unchanged(client, admin_user, rent_setup, amount):
    _, payload = rent_setup
    charge = create_charge(client, admin_user, payload)
    assert client.put(f"/rent/{charge['id']}/payment", headers=auth_headers(admin_user), json={"paid_amount_minor": amount}).status_code == 422
    assert client.get(f"/rent/{charge['id']}", headers=auth_headers(admin_user)).json()["paid_amount_minor"] == 0


def test_rent_authorization_and_ownership(client, db_session, admin_user, tenant_user, rent_setup):
    apartment, payload = rent_setup
    charge = create_charge(client, admin_user, payload)
    other = User(full_name="Other", email="other@example.com", password_hash="unused", role="tenant", apartment_id=apartment.id)
    db_session.add(other)
    db_session.commit()
    other_headers = auth_headers(other)
    assert client.get("/rent/").status_code == 401
    assert client.post("/rent/", headers=auth_headers(tenant_user), json=payload).status_code == 403
    assert client.put(f"/rent/{charge['id']}/payment", headers=auth_headers(tenant_user), json={"paid_amount_minor": 100}).status_code == 403
    assert client.get("/rent/", headers=other_headers).json() == []
    assert client.get(f"/rent/{charge['id']}", headers=other_headers).status_code == 404
    assert client.get(f"/rent/?tenant_id={tenant_user.id}", headers=other_headers).status_code == 403


@pytest.mark.parametrize("case", ["inactive", "unassigned", "admin", "missing"])
def test_charge_requires_assigned_active_tenant(client, db_session, admin_user, tenant_user, rent_setup, case):
    _, payload = rent_setup
    if case == "inactive":
        tenant_user.is_active = False
    elif case == "unassigned":
        tenant_user.apartment_id = None
    elif case == "admin":
        payload["tenant_id"] = admin_user.id
    else:
        payload["tenant_id"] = 999
    db_session.commit()
    assert client.post("/rent/", headers=auth_headers(admin_user), json=payload).status_code == (404 if case == "missing" else 409)


def test_rent_history_survives_move_and_prevents_apartment_deletion(client, db_session, admin_user, tenant_user, rent_setup):
    apartment, payload = rent_setup
    charge = create_charge(client, admin_user, payload)
    other, _ = create_apartment_and_room(db_session, "Other")
    headers = auth_headers(admin_user)
    assert client.put(f"/users/{tenant_user.id}/apartment", headers=headers, json={"apartment_id": other.id}).status_code == 200
    history = client.get(f"/rent/{charge['id']}", headers=auth_headers(tenant_user)).json()
    assert history["apartment_id"] == apartment.id
    assert client.delete(f"/apartments/{apartment.id}", headers=headers).status_code == 409


def test_rent_list_pagination_and_missing_record(client, admin_user, rent_setup):
    _, payload = rent_setup
    create_charge(client, admin_user, payload)
    create_charge(client, admin_user, {**payload, "period": "2026-10"})
    headers = auth_headers(admin_user)
    first = client.get("/rent/?limit=1", headers=headers).json()
    second = client.get("/rent/?limit=1&offset=1", headers=headers).json()
    assert first[0]["id"] != second[0]["id"]
    assert client.get("/rent/?limit=201", headers=headers).status_code == 422
    assert client.get("/rent/999", headers=headers).status_code == 404
    assert client.put("/rent/999/payment", headers=headers, json={"paid_amount_minor": 0}).status_code == 404
