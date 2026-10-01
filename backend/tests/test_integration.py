from backend.tests.test_devices import auth_headers


def test_complete_apartment_management_flow(client, admin_user):
    admin = auth_headers(admin_user)
    tenant_data = {"full_name": "Demo Tenant", "email": "demo@example.com", "password": "StrongPassword123!"}
    registration = client.post("/users/register", json=tenant_data)
    assert registration.status_code == 201
    tenant_id = registration.json()["id"]
    assert registration.json()["role"] == "tenant"
    login = client.post("/users/login", json={"email": tenant_data["email"], "password": tenant_data["password"]})
    assert login.status_code == 200
    tenant = {"Authorization": "Bearer " + login.json()["access_token"]}
    apartment = client.post("/apartments/", headers=admin, json={"name": "Demo 101", "floor": 1}).json()
    aid = apartment["id"]
    assert client.put(f"/users/{tenant_id}/apartment", headers=admin, json={"apartment_id": aid}).status_code == 200
    room = client.post(f"/apartments/{aid}/rooms/", headers=admin, json={"name": "Living room", "type": "living_room"}).json()
    device_url = f"/apartments/{aid}/rooms/{room['id']}/devices/"
    switch = client.post(device_url, headers=admin, json={"name": "Switch", "type": "switch", "is_online": True}).json()
    light = client.post(device_url, headers=admin, json={"name": "Light", "type": "light", "is_online": True}).json()
    rule = client.post(f"/apartments/{aid}/automations/", headers=admin, json={
        "name": "Light follows switch", "source_device_id": switch["id"], "source_power": "on",
        "target_device_id": light["id"], "target_power": "on",
    })
    assert rule.status_code == 201
    assert client.put(device_url + str(switch["id"]) + "/state", headers=tenant, json={"power": "on"}).status_code == 200
    assert client.get(device_url + str(light["id"]) + "/state", headers=tenant).json()["power"] == "on"
    charge = client.post("/rent/", headers=admin, json={"tenant_id": tenant_id, "period": "2026-09", "due_date": "2000-01-01", "currency": "XAF", "amount_minor": 75000})
    assert charge.status_code == 201
    assert charge.json()["status"] == "overdue"
    assert client.put(f"/rent/{charge.json()['id']}/payment", headers=admin, json={"paid_amount_minor": 75000}).json()["status"] == "paid"
    summary = client.get("/dashboard/summary", headers=tenant).json()
    assert summary["powered_on_devices"] == 2
    assert summary["enabled_rules"] == 1
    assert summary["occupied_apartments"] == 1
    assert summary["rent_balances"][0]["outstanding_minor"] == 0
    assert client.delete(f"/users/{tenant_id}/apartment", headers=admin).status_code == 200
    assert client.get(f"/apartments/{aid}", headers=admin).json()["status"] == "available"
    assert client.get(device_url, headers=tenant).status_code == 403
    assert len(client.get("/rent/", headers=tenant).json()) == 1
