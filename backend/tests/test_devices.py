from backend.app.models.apartment import Apartment
from backend.app.models.device import Device
from backend.app.models.room import Room
from backend.app.models.user import User
from backend.app.services.jwt import create_access_token


def auth_headers(user: User):
    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}


def create_apartment_and_room(db_session, name="Apartment 1"):
    apartment = Apartment(
        name=name,
        floor=1,
        status="occupied",
    )
    db_session.add(apartment)
    db_session.commit()
    db_session.refresh(apartment)

    room = Room(
        name="Living Room",
        type="living_room",
        apartment_id=apartment.id,
    )
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)

    return apartment, room


def create_device(db_session, room_id, name="Living Room Light"):
    device = Device(
        name=name,
        type="light",
        room_id=room_id,
        is_online=True,
        is_enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


def test_admin_can_create_device(client, db_session, admin_user):
    apartment, room = create_apartment_and_room(db_session)

    response = client.post(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/",
        json={
            "name": "Living Room Light",
            "type": "light",
            "is_online": True,
            "is_enabled": True,
        },
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Living Room Light"
    assert data["type"] == "light"
    assert data["room_id"] == room.id
    assert data["is_online"] is True
    assert data["is_enabled"] is True


def test_tenant_cannot_create_device(
    client,
    db_session,
    tenant_user,
):
    apartment, room = create_apartment_and_room(db_session)

    tenant_user.apartment_id = apartment.id
    db_session.commit()

    response = client.post(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/",
        json={
            "name": "Camera",
            "type": "camera",
        },
        headers=auth_headers(tenant_user),
    )

    assert response.status_code == 403


def test_create_device_requires_authentication(
    client,
    db_session,
):
    apartment, room = create_apartment_and_room(db_session)

    response = client.post(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/",
        json={
            "name": "Camera",
            "type": "camera",
        },
    )

    assert response.status_code == 401


def test_create_device_in_nonexistent_room_returns_404(
    client,
    admin_user,
):
    response = client.post(
        "/apartments/999/rooms/999/devices/",
        json={
            "name": "Camera",
            "type": "camera",
        },
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found."


def test_admin_can_list_devices(
    client,
    db_session,
    admin_user,
):
    apartment, room = create_apartment_and_room(db_session)
    device = create_device(db_session, room.id)

    response = client.get(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == device.id
    assert data[0]["name"] == device.name


def test_tenant_can_list_devices_in_own_apartment(
    client,
    db_session,
    tenant_user,
):
    apartment, room = create_apartment_and_room(db_session)

    tenant_user.apartment_id = apartment.id
    db_session.commit()

    device = create_device(db_session, room.id)

    response = client.get(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/",
        headers=auth_headers(tenant_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == device.id


def test_tenant_cannot_list_devices_in_other_apartment(
    client,
    db_session,
    tenant_user,
):
    apartment, room = create_apartment_and_room(db_session)

    other_apartment, other_room = create_apartment_and_room(
        db_session,
        name="Apartment 2",
    )

    tenant_user.apartment_id = apartment.id
    db_session.commit()

    create_device(db_session, other_room.id)

    response = client.get(
        f"/apartments/{other_apartment.id}/rooms/{other_room.id}/devices/",
        headers=auth_headers(tenant_user),
    )

    assert response.status_code == 403


def test_admin_can_get_single_device(
    client,
    db_session,
    admin_user,
):
    apartment, room = create_apartment_and_room(db_session)
    device = create_device(db_session, room.id)

    response = client.get(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/{device.id}",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == device.id
    assert data["name"] == device.name
    assert data["type"] == device.type


def test_get_nonexistent_device_returns_404(
    client,
    db_session,
    admin_user,
):
    apartment, room = create_apartment_and_room(db_session)

    response = client.get(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/999",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found."


def test_admin_can_update_device(
    client,
    db_session,
    admin_user,
):
    apartment, room = create_apartment_and_room(db_session)
    device = create_device(db_session, room.id)

    response = client.patch(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/{device.id}",
        json={
            "name": "Main Camera",
            "type": "camera",
            "is_online": False,
        },
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Main Camera"
    assert data["type"] == "camera"
    assert data["is_online"] is False
    assert data["is_enabled"] is True


def test_tenant_cannot_update_device(
    client,
    db_session,
    tenant_user,
):
    apartment, room = create_apartment_and_room(db_session)

    tenant_user.apartment_id = apartment.id
    db_session.commit()

    device = create_device(db_session, room.id)

    response = client.patch(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/{device.id}",
        json={
            "name": "Changed Device",
        },
        headers=auth_headers(tenant_user),
    )

    assert response.status_code == 403


def test_admin_can_delete_device(
    client,
    db_session,
    admin_user,
):
    apartment, room = create_apartment_and_room(db_session)
    device = create_device(db_session, room.id)

    response = client.delete(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/{device.id}",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 204

    deleted_device = (
        db_session.query(Device)
        .filter(Device.id == device.id)
        .first()
    )

    assert deleted_device is None


def test_tenant_cannot_delete_device(
    client,
    db_session,
    tenant_user,
):
    apartment, room = create_apartment_and_room(db_session)

    tenant_user.apartment_id = apartment.id
    db_session.commit()

    device = create_device(db_session, room.id)

    response = client.delete(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/{device.id}",
        headers=auth_headers(tenant_user),
    )

    assert response.status_code == 403


def test_device_from_wrong_room_returns_404(
    client,
    db_session,
    admin_user,
):
    apartment, room = create_apartment_and_room(db_session)

    second_room = Room(
        name="Bedroom",
        type="bedroom",
        apartment_id=apartment.id,
    )
    db_session.add(second_room)
    db_session.commit()
    db_session.refresh(second_room)

    device = create_device(
        db_session,
        second_room.id,
        name="Bedroom Light",
    )

    response = client.get(
        f"/apartments/{apartment.id}/rooms/{room.id}/devices/{device.id}",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found."
