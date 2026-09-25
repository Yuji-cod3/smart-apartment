from fastapi.testclient import TestClient

from backend.app.models.apartment import Apartment
from backend.app.services.auth import hash_password
from backend.app.services.jwt import create_access_token
from backend.app.services.auth import verify_password
from backend.app.models.user import User, UserRole

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
def test_get_users_requires_admin(
    client: TestClient,
):
    response = client.get("/users/")

    assert response.status_code == 401


def test_tenant_cannot_get_users(
    client: TestClient,
):
    response = client.post(
        "/users/register",
        json={
            "full_name": "Regular Tenant",
            "email": "regular-user-list@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201

    user_id = response.json()["id"]

    from backend.app.services.jwt import create_access_token

    token = create_access_token(
        user_id=user_id,
        role="tenant",
    )

    response = client.get(
        "/users/",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


def test_admin_can_get_users(
    client: TestClient,
    admin_user,
):
    from backend.app.services.jwt import create_access_token

    token = create_access_token(
        user_id=admin_user.id,
        role=admin_user.role,
    )

    response = client.get(
        "/users/",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1
def test_assign_apartment_requires_admin(
    client: TestClient,
):
    response = client.post(
        "/users/register",
        json={
            "full_name": "Assignment Tenant",
            "email": "assignment-auth@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201

    user_id = response.json()["id"]

    from backend.app.services.jwt import create_access_token

    token = create_access_token(
        user_id=user_id,
        role="tenant",
    )

    response = client.put(
        f"/users/{user_id}/apartment",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "apartment_id": 1,
        },
    )

    assert response.status_code == 403


def test_admin_can_assign_tenant_to_apartment(
    client: TestClient,
    admin_user,
):
    apartment_response = client.post(
        "/apartments/",
        headers={
            "Authorization": (
                "Bearer "
                + create_access_token(
                    user_id=admin_user.id,
                    role=admin_user.role,
                )
            )
        },
        json={
            "name": "Assignment Apartment",
            "floor": 1,
            "status": "available",
        },
    )

    assert apartment_response.status_code == 201

    apartment_id = apartment_response.json()["id"]

    tenant_response = client.post(
        "/users/register",
        json={
            "full_name": "Assigned Tenant",
            "email": "assigned-tenant@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert tenant_response.status_code == 201

    tenant_id = tenant_response.json()["id"]

    admin_token = create_access_token(
        user_id=admin_user.id,
        role=admin_user.role,
    )

    response = client.put(
        f"/users/{tenant_id}/apartment",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        json={
            "apartment_id": apartment_id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == tenant_id
    assert data["apartment_id"] == apartment_id
    assert data["role"] == "tenant"


def test_assign_apartment_rejects_unknown_user(
    client: TestClient,
    admin_user,
):
    from backend.app.services.jwt import create_access_token

    admin_token = create_access_token(
        user_id=admin_user.id,
        role=admin_user.role,
    )

    response = client.put(
        "/users/99999/apartment",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        json={
            "apartment_id": 1,
        },
    )

    assert response.status_code == 404


def test_assign_apartment_rejects_unknown_apartment(
    client: TestClient,
    admin_user,
):
    tenant_response = client.post(
        "/users/register",
        json={
            "full_name": "Unknown Apartment Tenant",
            "email": "unknown-apartment@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert tenant_response.status_code == 201

    tenant_id = tenant_response.json()["id"]

    from backend.app.services.jwt import create_access_token

    admin_token = create_access_token(
        user_id=admin_user.id,
        role=admin_user.role,
    )

    response = client.put(
        f"/users/{tenant_id}/apartment",
        headers={
            "Authorization": f"Bearer {admin_token}",
        },
        json={
            "apartment_id": 99999,
        },
    )

    assert response.status_code == 404
def test_remove_apartment_assignment_requires_authentication(client):
    response = client.delete("/users/1/apartment")

    assert response.status_code == 401


def test_tenant_cannot_remove_apartment_assignment(
    client,
    db_session,
):
    tenant = User(
        full_name="Test Tenant",
        email="remove-tenant@example.com",
        password_hash=hash_password("StrongPassword123!"),
        role=UserRole.TENANT,
        is_active=True,
        apartment_id=None,
    )

    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    login_response = client.post(
        "/users/login",
        json={
            "email": "remove-tenant@example.com",
            "password": "StrongPassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.delete(
        f"/users/{tenant.id}/apartment",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


def test_admin_can_remove_apartment_assignment(
    client,
    db_session,
    admin_user,
):
    apartment = Apartment(
        name="Apartment 101",
        floor=1,
        status="occupied",
    )

    tenant = User(
        full_name="Assigned Tenant",
        email="assigned-remove@example.com",
        password_hash=hash_password("StrongPassword123!"),
        role=UserRole.TENANT,
        is_active=True,
    )

    db_session.add(apartment)
    db_session.add(tenant)
    db_session.commit()

    tenant.apartment_id = apartment.id
    db_session.commit()
    db_session.refresh(tenant)

    login_response = client.post(
        "/users/login",
        json={
            "email": admin_user.email,
            "password": "StrongPassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.delete(
        f"/users/{tenant.id}/apartment",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == tenant.id
    assert data["apartment_id"] is None


def test_remove_apartment_assignment_unknown_user(
    client,
    admin_user,
):
    login_response = client.post(
        "/users/login",
        json={
            "email": admin_user.email,
            "password": "StrongPassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.delete(
        "/users/99999/apartment",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404


def test_remove_apartment_assignment_rejects_admin_target(
    client,
    admin_user,
):
    response = client.delete(
        f"/users/{admin_user.id}/apartment",
        headers={
            "Authorization": f"Bearer {create_access_token(
                user_id=admin_user.id,
                role="admin",
            )}",
        },
    )

    assert response.status_code == 400


def test_remove_apartment_assignment_rejects_unassigned_tenant(
    client,
    db_session,
    admin_user,
):
    tenant = User(
        full_name="Unassigned Tenant",
        email="unassigned-remove@example.com",
        password_hash=hash_password("StrongPassword123!"),
        role=UserRole.TENANT,
        is_active=True,
        apartment_id=None,
    )

    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    token = create_access_token(
        user_id=admin_user.id,
        role="admin",
    )

    response = client.delete(
        f"/users/{tenant.id}/apartment",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 400
