from fastapi import HTTPException

from backend.app.models.user import User
from backend.app.services.authorization import require_admin


def test_tenant_is_rejected():
    tenant = User(
        id=1,
        full_name="Test Tenant",
        email="tenant@example.com",
        password_hash="fake-hash",
        role="tenant",
        is_active=True,
    )

    try:
        require_admin(current_user=tenant)
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_admin_is_allowed():
    admin = User(
        id=2,
        full_name="Test Admin",
        email="admin@example.com",
        password_hash="fake-hash",
        role="admin",
        is_active=True,
    )

    result = require_admin(current_user=admin)

    assert result is admin
