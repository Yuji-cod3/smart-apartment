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
    register_response = client.post(
        "/users/register",
        json={
            "full_name": "Regular Tenant",
            "email": "tenant-create-test@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert register_response.status_code == 201

    token = create_access_token(
        user_id=register_response.json()["id"],
        role="tenant",
    )

    response = client.post(
        "/apartments/",
        headers={
            "Authorization": f"Bearer {token}",
        },
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
    register_response = client.post(
        "/users/register",
        json={
            "full_name": "Apartment Viewer",
            "email": "viewer@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert register_response.status_code == 201

    token = create_access_token(
        user_id=register_response.json()["id"],
        role="tenant",
    )

    response = client.get(
        "/apartments/",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
