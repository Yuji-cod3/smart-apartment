from fastapi.testclient import TestClient

from backend.app.services.auth import verify_password
from backend.app.models.user import User

def test_register_user(client: TestClient):
    response = client.post(
        "/users/register",
        json={
            "full_name": "Test Tenant",
            "email": "testtenant@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["full_name"] == "Test Tenant"
    assert data["email"] == "testtenant@example.com"
    assert data["role"] == "tenant"
    assert data["is_active"] is True
    assert data["apartment_id"] is None

    # Sensitive password data must never appear in the API response.
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_email(client: TestClient):
    user = {
        "full_name": "First Tenant",
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
    }

    first_response = client.post(
        "/users/register",
        json=user,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/users/register",
        json=user,
    )

    assert second_response.status_code == 409


def test_invalid_email(client: TestClient):
    response = client.post(
        "/users/register",
        json={
            "full_name": "Invalid Email User",
            "email": "not-an-email",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 422


def test_short_password(client: TestClient):
    response = client.post(
        "/users/register",
        json={
            "full_name": "Weak Password User",
            "email": "weak@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422
def test_password_is_hashed(client: TestClient):
    password = "StrongPassword123!"

    response = client.post(
        "/users/register",
        json={
            "full_name": "Hash Test User",
            "email": "hash-test@example.com",
            "password": password,
        },
    )

    assert response.status_code == 201

    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.email == "hash-test@example.com")
            .first()
        )

        assert user is not None

        # The plaintext password must never be stored.
        assert user.password_hash != password

        # The stored hash must successfully verify
        # against the original password.
        assert verify_password(
            password,
            user.password_hash,
        )

        # A wrong password must fail verification.
        assert not verify_password(
            "WrongPassword123!",
            user.password_hash,
        )

    finally:
        db.close()
def test_password_is_hashed(client: TestClient, db_session):
    password = "StrongPassword123!"

    response = client.post(
        "/users/register",
        json={
            "full_name": "Hash Test User",
            "email": "hash-test@example.com",
            "password": password,
        },
    )

    assert response.status_code == 201

    user = (
        db_session.query(User)
        .filter(User.email == "hash-test@example.com")
        .first()
    )

    assert user is not None

    # The plaintext password must never be stored.
    assert user.password_hash != password

    # The original password must successfully verify.
    assert verify_password(
        password,
        user.password_hash,
    )

    # An incorrect password must fail.
    assert not verify_password(
        "WrongPassword123!",
        user.password_hash,
    )
def test_user_login(client: TestClient):
    client.post(
        "/users/register",
        json={
            "full_name": "Login Test User",
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    response = client.post(
        "/users/login",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    client.post(
        "/users/register",
        json={
            "full_name": "Wrong Password User",
            "email": "wrong-password@example.com",
            "password": "StrongPassword123!",
        },
    )

    response = client.post(
        "/users/login",
        json={
            "email": "wrong-password@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_unknown_email(client: TestClient):
    response = client.post(
        "/users/login",
        json={
            "email": "doesnotexist@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401
