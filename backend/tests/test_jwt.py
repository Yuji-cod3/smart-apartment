import jwt
from fastapi import HTTPException

from backend.app.config import settings
from backend.app.models.user import User
from backend.app.services.jwt import create_access_token
from backend.app.services.security import get_current_user


def test_create_access_token():
    token = create_access_token(
        user_id=123,
        role="tenant",
    )

    assert isinstance(token, str)
    assert token


def test_access_token_contains_expected_data():
    token = create_access_token(
        user_id=123,
        role="tenant",
    )

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == "123"
    assert payload["role"] == "tenant"
    assert "exp" in payload


def test_get_current_user():
    user = User(
        id=1,
        full_name="Test Tenant",
        email="security@example.com",
        password_hash="fake-hash",
        role="tenant",
        is_active=True,
    )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    credentials = type(
        "Credentials",
        (),
        {"credentials": token},
    )()

    class FakeQuery:
        def filter(self, *args):
            return self

        def first(self):
            return user

    class FakeDB:
        def query(self, model):
            return FakeQuery()

    result = get_current_user(
        credentials=credentials,
        db=FakeDB(),
    )

    assert result is user


def test_invalid_token():
    credentials = type(
        "Credentials",
        (),
        {"credentials": "not-a-real-token"},
    )()

    class FakeDB:
        pass

    try:
        get_current_user(
            credentials=credentials,
            db=FakeDB(),
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401
