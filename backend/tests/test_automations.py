import pytest
from backend.app.models.automation import AutomationRule
from backend.tests.test_devices import auth_headers, create_apartment_and_room, create_device


@pytest.fixture
def automation_setup(db_session, tenant_user):
    apartment, room = create_apartment_and_room(db_session)
    source = create_device(db_session, room.id, "Switch")
    target = create_device(db_session, room.id, "Light")
    tenant_user.apartment_id = apartment.id
    db_session.commit()
    payload = {"name": "Switch turns on light", "source_device_id": source.id, "source_power": "on",
               "target_device_id": target.id, "target_power": "on"}
    return apartment, room, source, target, payload


def add_rule(client, admin_user, setup, **updates):
    apartment, _, _, _, payload = setup
    response = client.post(f"/apartments/{apartment.id}/automations/", headers=auth_headers(admin_user), json={**payload, **updates})
    assert response.status_code == 201, response.text
    return response.json()


def test_control_triggers_rule_atomically(client, db_session, admin_user, tenant_user, automation_setup):
    apartment, room, source, target, _ = automation_setup
    add_rule(client, admin_user, automation_setup)
    response = client.put(f"/apartments/{apartment.id}/rooms/{room.id}/devices/{source.id}/state",
                          headers=auth_headers(tenant_user), json={"power": "on"})
    assert response.status_code == 200
    db_session.refresh(target)
    assert target.power == "on"
    result = client.post(f"/apartments/{apartment.id}/automations/evaluate", headers=auth_headers(tenant_user))
    assert result.json()["results"][0]["outcome"] == "unchanged"


def test_snapshot_has_no_chaining_and_first_rule_wins(client, db_session, admin_user, automation_setup):
    apartment, room, source, target, _ = automation_setup
    third = create_device(db_session, room.id, "Third")
    source.power = "on"
    db_session.commit()
    add_rule(client, admin_user, automation_setup)
    add_rule(client, admin_user, automation_setup, target_power="off")
    add_rule(client, admin_user, automation_setup, source_device_id=target.id, target_device_id=third.id)
    # Cycle is safe because actions never recursively trigger another evaluation.
    add_rule(client, admin_user, automation_setup, source_device_id=target.id, target_device_id=source.id, target_power="off")
    response = client.post(f"/apartments/{apartment.id}/automations/evaluate", headers=auth_headers(admin_user))
    assert [r["outcome"] for r in response.json()["results"]] == ["applied", "conflict", "not_matched", "not_matched"]
    assert third.power == "off"
    assert source.power == "on"


@pytest.mark.parametrize("case,outcome", [("disabled", "disabled"), ("offline_source", "unavailable"), ("offline_target", "unavailable"), ("not_matched", "not_matched")])
def test_rule_outcomes(client, db_session, admin_user, automation_setup, case, outcome):
    apartment, _, source, target, _ = automation_setup
    add_rule(client, admin_user, automation_setup, is_enabled=case != "disabled")
    if case == "offline_source":
        source.is_online = False
    if case == "offline_target":
        target.is_online = False
    db_session.commit()
    response = client.post(f"/apartments/{apartment.id}/automations/evaluate", headers=auth_headers(admin_user))
    assert response.json()["results"][0]["outcome"] == outcome
    assert target.power == "off"


def test_rule_lifecycle_and_admin_permissions(client, db_session, admin_user, tenant_user, automation_setup):
    apartment, _, _, _, payload = automation_setup
    url = f"/apartments/{apartment.id}/automations/"
    assert client.post(url, json=payload).status_code == 401
    assert client.post(url, json=payload, headers=auth_headers(tenant_user)).status_code == 403
    rule = add_rule(client, admin_user, automation_setup)
    assert len(client.get(url, headers=auth_headers(tenant_user)).json()) == 1
    detail = url + str(rule["id"])
    assert client.put(detail, json=payload, headers=auth_headers(tenant_user)).status_code == 403
    assert client.delete(detail, headers=auth_headers(tenant_user)).status_code == 403
    assert client.put(detail, json={**payload, "is_enabled": False}, headers=auth_headers(admin_user)).json()["is_enabled"] is False
    assert client.delete(detail, headers=auth_headers(admin_user)).status_code == 204
    assert client.delete(detail, headers=auth_headers(admin_user)).status_code == 404
    tenant_user.apartment_id = None
    db_session.commit()
    assert client.get(url, headers=auth_headers(tenant_user)).status_code == 403
    assert client.post(url + "evaluate", headers=auth_headers(tenant_user)).status_code == 403


def test_rule_rejects_cross_apartment_and_self_reference(client, db_session, admin_user, automation_setup):
    apartment, _, source, _, payload = automation_setup
    other, room = create_apartment_and_room(db_session, "Other")
    outside = create_device(db_session, room.id)
    url = f"/apartments/{apartment.id}/automations/"
    headers = auth_headers(admin_user)
    assert client.post(url, json={**payload, "target_device_id": outside.id}, headers=headers).status_code == 404
    assert client.post(url, json={**payload, "target_device_id": source.id}, headers=headers).status_code == 422
    source.type = "camera"
    db_session.commit()
    assert client.post(url, json=payload, headers=headers).status_code == 422


@pytest.mark.parametrize("level", ["device", "room", "apartment"])
def test_parent_deletion_removes_rules(client, db_session, admin_user, automation_setup, level):
    apartment, room, source, _, _ = automation_setup
    add_rule(client, admin_user, automation_setup)
    url = f"/apartments/{apartment.id}"
    if level in ("device", "room"):
        url += f"/rooms/{room.id}"
    if level == "device":
        url += f"/devices/{source.id}"
    assert client.delete(url, headers=auth_headers(admin_user)).status_code == 204
    assert db_session.query(AutomationRule).count() == 0
