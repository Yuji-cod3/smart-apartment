from fastapi.testclient import TestClient

from backend.app.models.user import User
from backend.app.services.jwt import create_access_token


def admin_headers(admin_user):
    token = create_access_token(
        user_id=admin_user.id,
        role=admin_user.role,
    )
    return {"Authorization": f"Bearer {token}"}


def tenant_headers(client: TestClient, email: str):
    response = client.post(
        "/users/register",
        json={
            "full_name": "Test Tenant",
            "email": email,
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201

    token = create_access_token(
        user_id=response.json()["id"],
        role="tenant",
    )

    return {"Authorization": f"Bearer {token}"}


def create_test_apartment(client, admin_headers_value, name="Apartment 101"):
    response = client.post(
        "/apartments/",
        json={
            "name": name,
            "floor": 1,
            "status": "available",
        },
        headers=admin_headers_value,
    )

    assert response.status_code == 201
    return response.json()


def test_admin_can_create_room(client, admin_user):
    headers = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        headers,
    )

    response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Living Room",
            "type": "living_room",
        },
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Living Room"
    assert data["type"] == "living_room"
    assert data["apartment_id"] == apartment["id"]


def test_tenant_cannot_create_room(client, admin_user):
    admin_headers_value = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        admin_headers_value,
    )

    tenant_headers_value = tenant_headers(
        client,
        "tenant-room-create@example.com",
    )

    response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Bedroom",
            "type": "bedroom",
        },
        headers=tenant_headers_value,
    )

    assert response.status_code == 403


def test_create_room_requires_authentication(client, admin_user):
    admin_headers_value = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        admin_headers_value,
    )

    response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Kitchen",
            "type": "kitchen",
        },
    )

    assert response.status_code == 401


def test_create_room_for_nonexistent_apartment(client, admin_user):
    headers = admin_headers(admin_user)

    response = client.post(
        "/apartments/9999/rooms/",
        json={
            "name": "Bedroom",
            "type": "bedroom",
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_get_rooms_requires_authentication(client, admin_user):
    admin_headers_value = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        admin_headers_value,
    )

    response = client.get(
        f"/apartments/{apartment['id']}/rooms/",
    )

    assert response.status_code == 401


def test_admin_can_get_rooms(client, admin_user):
    headers = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        headers,
    )

    client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Living Room",
            "type": "living_room",
        },
        headers=headers,
    )

    response = client.get(
        f"/apartments/{apartment['id']}/rooms/",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Living Room"


def test_tenant_can_get_rooms_in_own_apartment(
    client,
    admin_user,
    db_session,
):
    admin_headers_value = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        admin_headers_value,
    )

    tenant_headers_value = tenant_headers(
        client,
        "tenant-own-room@example.com",
    )

    tenant = (
        db_session.query(User)
        .filter(User.email == "tenant-own-room@example.com")
        .first()
    )

    tenant.apartment_id = apartment["id"]
    db_session.commit()

    client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Bedroom",
            "type": "bedroom",
        },
        headers=admin_headers_value,
    )

    response = client.get(
        f"/apartments/{apartment['id']}/rooms/",
        headers=tenant_headers_value,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Bedroom"


def test_tenant_cannot_get_rooms_from_other_apartment(
    client,
    admin_user,
    db_session,
):
    admin_headers_value = admin_headers(admin_user)

    apartment_a = create_test_apartment(
        client,
        admin_headers_value,
        "Apartment A",
    )

    apartment_b = create_test_apartment(
        client,
        admin_headers_value,
        "Apartment B",
    )

    tenant_headers_value = tenant_headers(
        client,
        "tenant-other-room@example.com",
    )

    tenant = (
        db_session.query(User)
        .filter(User.email == "tenant-other-room@example.com")
        .first()
    )

    tenant.apartment_id = apartment_a["id"]
    db_session.commit()

    response = client.get(
        f"/apartments/{apartment_b['id']}/rooms/",
        headers=tenant_headers_value,
    )

    assert response.status_code == 403


def test_get_single_room(client, admin_user):
    headers = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        headers,
    )

    create_response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Kitchen",
            "type": "kitchen",
        },
        headers=headers,
    )

    room = create_response.json()

    response = client.get(
        f"/apartments/{apartment['id']}/rooms/{room['id']}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == room["id"]
    assert data["name"] == "Kitchen"


def test_get_nonexistent_room(client, admin_user):
    headers = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        headers,
    )

    response = client.get(
        f"/apartments/{apartment['id']}/rooms/9999",
        headers=headers,
    )

    assert response.status_code == 404


def test_admin_can_update_room(client, admin_user):
    headers = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        headers,
    )

    create_response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Bedroom",
            "type": "bedroom",
        },
        headers=headers,
    )

    room = create_response.json()

    response = client.patch(
        f"/apartments/{apartment['id']}/rooms/{room['id']}",
        json={
            "name": "Master Bedroom",
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Master Bedroom"
    assert data["type"] == "bedroom"


def test_tenant_cannot_update_room(
    client,
    admin_user,
    db_session,
):
    admin_headers_value = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        admin_headers_value,
    )

    create_response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Bedroom",
            "type": "bedroom",
        },
        headers=admin_headers_value,
    )

    room = create_response.json()

    tenant_headers_value = tenant_headers(
        client,
        "tenant-room-update@example.com",
    )

    tenant = (
        db_session.query(User)
        .filter(User.email == "tenant-room-update@example.com")
        .first()
    )

    tenant.apartment_id = apartment["id"]
    db_session.commit()

    response = client.patch(
        f"/apartments/{apartment['id']}/rooms/{room['id']}",
        json={
            "name": "Hacked Room",
        },
        headers=tenant_headers_value,
    )

    assert response.status_code == 403


def test_admin_can_delete_room(client, admin_user):
    headers = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        headers,
    )

    create_response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Bathroom",
            "type": "bathroom",
        },
        headers=headers,
    )

    room = create_response.json()

    delete_response = client.delete(
        f"/apartments/{apartment['id']}/rooms/{room['id']}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/apartments/{apartment['id']}/rooms/{room['id']}",
        headers=headers,
    )

    assert get_response.status_code == 404


def test_tenant_cannot_delete_room(
    client,
    admin_user,
    db_session,
):
    admin_headers_value = admin_headers(admin_user)

    apartment = create_test_apartment(
        client,
        admin_headers_value,
    )

    create_response = client.post(
        f"/apartments/{apartment['id']}/rooms/",
        json={
            "name": "Bathroom",
            "type": "bathroom",
        },
        headers=admin_headers_value,
    )

    room = create_response.json()

    tenant_headers_value = tenant_headers(
        client,
        "tenant-room-delete@example.com",
    )

    tenant = (
        db_session.query(User)
        .filter(User.email == "tenant-room-delete@example.com")
        .first()
    )

    tenant.apartment_id = apartment["id"]
    db_session.commit()

    response = client.delete(
        f"/apartments/{apartment['id']}/rooms/{room['id']}",
        headers=tenant_headers_value,
    )

    assert response.status_code == 403
