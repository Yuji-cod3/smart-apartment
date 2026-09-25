import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.connection import Base
from backend.app.database.dependencies import get_db
from backend.app.main import app
from backend.app.models.user import User, UserRole
from backend.app.services.auth import hash_password


TEST_DATABASE_URL = "sqlite://"


engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)


TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session):
    admin = User(
        full_name="Test Admin",
        email="test-admin@example.com",
        password_hash=hash_password("StrongPassword123!"),
        role=UserRole.ADMIN,
    )

    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    return admin
