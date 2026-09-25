from fastapi.testclient import TestClient

from backend.app.services.jwt import create_access_token


def admin_headers(admin_user):
    token = create_access_token(
        user_id=admin_user.id,
        role=admin_user.role,
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def tenant_headers(client: TestClient, email: str):
    register_response = client.post(
        "/users/register",
        json={
            "full_name": "Regular Tenant",
            "email": email,
            "password": "StrongPassword123!",
        },
    )

    assert register_response.status_code == 201

    token = create_access_token(
        user_id=register_response.json()["id"],
        role="tenant",
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def create_test_apartment(
    client: TestClient,
    admin_user,
    name: str = "Test Apartment",
):
    response = client.post(
        "/apartments/",
        headers=admin_headers(admin_user),
        json={
            "name": name,
            "floor": 1,
            "status": "available",
        },
    )

    assert response.status_code == 201

    return response.json()


def test_health_check(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_apartment(client: TestClient, admin_user):
    response = client.post(
        "/apartments/",
        headers=admin_headers(admin_user),
        json={
            "name": "Test Apartment",
            "floor": 1,
            "status": "available",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Apartment"
    assert data["floor"] == 1
    assert data["status"] == "available"


def test_tenant_cannot_create_apartment(client: TestClient):
    headers = tenant_headers(
        client,
        "tenant-create-test@example.com",
    )

    response = client.post(
        "/apartments/",
        headers=headers,
        json={
            "name": "Tenant Apartment",
            "floor": 1,
            "status": "available",
        },
    )

    assert response.status_code == 403


def test_invalid_status(client: TestClient, admin_user):
    response = client.post(
        "/apartments/",
        headers=admin_headers(admin_user),
        json={
            "name": "Invalid Status Apartment",
            "floor": 1,
            "status": "banana",
        },
    )

    assert response.status_code == 422


def test_invalid_floor(client: TestClient, admin_user):
    response = client.post(
        "/apartments/",
        headers=admin_headers(admin_user),
        json={
            "name": "Invalid Floor Apartment",
            "floor": -5,
            "status": "available",
        },
    )

    assert response.status_code == 422


def test_get_apartments_requires_authentication(client: TestClient):
    response = client.get("/apartments/")

    assert response.status_code == 401


def test_get_apartments_with_valid_token(client: TestClient):
    headers = tenant_headers(
        client,
        "viewer@example.com",
    )

    response = client.get(
        "/apartments/",
        headers=headers,
    )

    assert response.status_code == 200


def test_update_apartment_requires_authentication(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Update Auth Apartment",
    )

    response = client.patch(
        f"/apartments/{apartment['id']}",
        json={
            "name": "Unauthorized Update",
        },
    )

    assert response.status_code == 401


def test_tenant_cannot_update_apartment(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Tenant Update Apartment",
    )

    headers = tenant_headers(
        client,
        "tenant-update@example.com",
    )

    response = client.patch(
        f"/apartments/{apartment['id']}",
        headers=headers,
        json={
            "name": "Tenant Modified Apartment",
        },
    )

    assert response.status_code == 403


def test_admin_can_update_apartment(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Admin Update Apartment",
    )

    response = client.patch(
        f"/apartments/{apartment['id']}",
        headers=admin_headers(admin_user),
        json={
            "name": "Updated Apartment",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Updated Apartment"


def test_delete_apartment_requires_authentication(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Delete Auth Apartment",
    )

    response = client.delete(
        f"/apartments/{apartment['id']}",
    )

    assert response.status_code == 401


def test_tenant_cannot_delete_apartment(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Tenant Delete Apartment",
    )

    headers = tenant_headers(
        client,
        "tenant-delete@example.com",
    )

    response = client.delete(
        f"/apartments/{apartment['id']}",
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_delete_apartment(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Admin Delete Apartment",
    )

    response = client.delete(
        f"/apartments/{apartment['id']}",
        headers=admin_headers(admin_user),
    )

    assert response.status_code == 204
def test_get_single_apartment_requires_authentication(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Single Apartment Auth Test",
    )

    response = client.get(
        f"/apartments/{apartment['id']}",
    )

    assert response.status_code == 401


def test_tenant_can_get_own_apartment(
    client: TestClient,
    admin_user,
    db_session,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Tenant Own Apartment",
    )

    headers = tenant_headers(
        client,
        "own-apartment@example.com",
    )

    from backend.app.models.user import User

    tenant = (
        db_session.query(User)
        .filter(User.email == "own-apartment@example.com")
        .first()
    )

    tenant.apartment_id = apartment["id"]
    db_session.commit()

    response = client.get(
        f"/apartments/{apartment['id']}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == apartment["id"]
    assert data["name"] == "Tenant Own Apartment"


def test_tenant_cannot_get_another_apartment(
    client: TestClient,
    admin_user,
    db_session,
):
    apartment_a = create_test_apartment(
        client,
        admin_user,
        "Tenant A Apartment",
    )

    apartment_b = create_test_apartment(
        client,
        admin_user,
        "Tenant B Apartment",
    )

    headers = tenant_headers(
        client,
        "tenant-a@example.com",
    )

    from backend.app.models.user import User

    tenant = (
        db_session.query(User)
        .filter(User.email == "tenant-a@example.com")
        .first()
    )

    tenant.apartment_id = apartment_a["id"]
    db_session.commit()

    response = client.get(
        f"/apartments/{apartment_b['id']}",
        headers=headers,
    )

    assert response.status_code == 403


def test_tenant_without_apartment_cannot_get_apartment(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Unassigned Tenant Apartment",
    )

    headers = tenant_headers(
        client,
        "unassigned@example.com",
    )

    response = client.get(
        f"/apartments/{apartment['id']}",
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_get_any_apartment(
    client: TestClient,
    admin_user,
):
    apartment = create_test_apartment(
        client,
        admin_user,
        "Admin View Apartment",
    )

    response = client.get(
        f"/apartments/{apartment['id']}",
        headers=admin_headers(admin_user),
    )

    assert response.status_code == 200
