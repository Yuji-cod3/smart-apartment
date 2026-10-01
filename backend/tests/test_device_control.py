import pytest

from backend.tests.test_devices import auth_headers, create_apartment_and_room, create_device


@pytest.fixture
def control_setup(db_session, tenant_user):
    apartment, room = create_apartment_and_room(db_session)
    tenant_user.apartment_id = apartment.id
    device = create_device(db_session, room.id)
    db_session.commit()
    return device, f"/apartments/{apartment.id}/rooms/{room.id}/devices/{device.id}/state"


def test_tenant_control_is_persisted_and_idempotent(client, tenant_user, control_setup):
    device, url = control_setup
    headers = auth_headers(tenant_user)
    assert client.get(url, headers=headers).json()["power"] == "off"
    first = client.put(url, headers=headers, json={"power": "on"})
    assert first.status_code == 200
    assert first.json()["power"] == "on"
    assert first.json()["state_updated_at"] is not None
    again = client.put(url, headers=headers, json={"power": "on"})
    assert again.json()["state_updated_at"] == first.json()["state_updated_at"]
    assert client.get(url, headers=headers).json()["power"] == "on"


@pytest.mark.parametrize("field,value", [("is_online", False), ("is_enabled", False), ("type", "camera")])
def test_control_rejects_unavailable_devices(client, db_session, tenant_user, control_setup, field, value):
    device, url = control_setup
    setattr(device, field, value)
    db_session.commit()
    response = client.put(url, headers=auth_headers(tenant_user), json={"power": "on"})
    assert response.status_code == 409
    assert device.power == "off"


@pytest.mark.parametrize("payload", [{"power": "toggle"}, {"power": None}, {}, {"power": "on", "is_enabled": True}])
def test_control_validation(client, tenant_user, control_setup, payload):
    _, url = control_setup
    assert client.put(url, headers=auth_headers(tenant_user), json=payload).status_code == 422


@pytest.mark.parametrize("method", ["get", "put"])
def test_state_requires_auth_and_apartment_access(client, db_session, tenant_user, control_setup, method):
    _, url = control_setup
    kwargs = {"json": {"power": "on"}} if method == "put" else {}
    assert getattr(client, method)(url, **kwargs).status_code == 401
    tenant_user.apartment_id = None
    db_session.commit()
    assert getattr(client, method)(url, headers=auth_headers(tenant_user), **kwargs).status_code == 403


def test_admin_control_and_wrong_parent(client, admin_user, control_setup):
    _, url = control_setup
    headers = auth_headers(admin_user)
    assert client.put(url, headers=headers, json={"power": "on"}).status_code == 200
    bad_url = url.replace("/apartments/1/", "/apartments/999/")
    assert client.put(bad_url, headers=headers, json={"power": "off"}).status_code == 404
