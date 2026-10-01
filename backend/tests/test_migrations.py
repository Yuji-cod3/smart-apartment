from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from backend.app.config import settings
from backend.app.database.connection import Base
from backend.app.main import app
from backend.app.database.dependencies import get_db


def migration_config(monkeypatch, tmp_path):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    return config, create_engine(url)


def test_fresh_upgrade_matches_models_and_downgrade(monkeypatch, tmp_path):
    config, engine = migration_config(monkeypatch, tmp_path)
    try:
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
        command.upgrade(config, "head")
        assert "rent_charges" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_upgrade_existing_data_and_new_feature_downgrade(monkeypatch, tmp_path):
    config, engine = migration_config(monkeypatch, tmp_path)
    try:
        command.upgrade(config, "4fb37f1d0a7f")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO apartments (id,name,floor,status) VALUES (1,'Existing',1,'occupied')"))
            connection.execute(text("INSERT INTO users (id,full_name,email,password_hash,role,is_active,apartment_id) VALUES (1,'Existing tenant','existing@example.com','unchanged','tenant',1,1)"))
            connection.execute(text("INSERT INTO rooms (id,name,type,apartment_id) VALUES (1,'Room','living_room',1)"))
            connection.execute(text("INSERT INTO devices (id,name,type,room_id,is_online,is_enabled) VALUES (1,'Light','light',1,1,1)"))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT power FROM devices WHERE id=1")).scalar_one() == "off"
            assert connection.execute(text("SELECT password_hash FROM users WHERE id=1")).scalar_one() == "unchanged"
        command.downgrade(config, "4fb37f1d0a7f")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT name FROM devices WHERE id=1")).scalar_one() == "Light"
            assert connection.execute(text("SELECT apartment_id FROM users WHERE id=1")).scalar_one() == 1
    finally:
        engine.dispose()


def test_readiness_returns_503_for_unmigrated_database(client):
    from sqlalchemy.orm import Session
    engine = create_engine("sqlite://")
    def empty_db():
        with Session(engine) as session:
            yield session
    previous = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = empty_db
    try:
        assert client.get("/health/ready").status_code == 503
    finally:
        app.dependency_overrides[get_db] = previous
        engine.dispose()


def test_readiness_returns_503_for_missing_columns(client):
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE devices DROP COLUMN state_updated_at"))
    def outdated_db():
        with Session(engine) as session:
            yield session
    previous = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = outdated_db
    try:
        assert client.get("/health/ready").status_code == 503
    finally:
        app.dependency_overrides[get_db] = previous
        engine.dispose()
