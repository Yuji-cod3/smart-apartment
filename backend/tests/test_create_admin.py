import pytest
from backend.app.create_admin import create_admin
from backend.app.schemas.user import UserCreate
from backend.app.services.auth import verify_password


def test_admin_bootstrap_hashes_password_and_rejects_existing_accounts(db_session):
    data = UserCreate(full_name="Initial Admin", email="initial@example.com", password="StrongPassword123!")
    user = create_admin(db_session, data)
    assert user.role == "admin"
    assert verify_password(data.password, user.password_hash)
    with pytest.raises(ValueError, match="already exists"):
        create_admin(db_session, data)
