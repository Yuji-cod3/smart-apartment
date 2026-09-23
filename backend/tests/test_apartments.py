from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_apartment(client: TestClient):
    response = client.post(
        "/apartments/",
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


def test_invalid_status(client: TestClient):
    response = client.post(
        "/apartments/",
        json={
            "name": "Invalid Status Apartment",
            "floor": 1,
            "status": "banana",
        },
    )

    assert response.status_code == 422


def test_invalid_floor(client: TestClient):
    response = client.post(
        "/apartments/",
        json={
            "name": "Invalid Floor Apartment",
            "floor": -5,
            "status": "available",
        },
    )

    assert response.status_code == 422
