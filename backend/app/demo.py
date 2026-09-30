"""Isolated, repeatable local demo. Run: python -m backend.app.demo."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets


def seed_demo(db, password):
    from backend.app.models.apartment import Apartment
    from backend.app.models.automation import AutomationRule
    from backend.app.models.device import Device
    from backend.app.models.rent import RentCharge
    from backend.app.models.room import Room
    from backend.app.models.user import User
    from backend.app.services.auth import hash_password

    # Never overwrite an existing demo or seed into a nonempty application database.
    if db.query(User).first() or db.query(Apartment).first():
        return False
    today = datetime.now(timezone.utc).date()
    admin = User(full_name="Alex Morgan", email="admin@demo.example.com", password_hash=hash_password(password), role="admin")
    db.add(admin)
    homes = [
        ("Garden 101", 1, "occupied", "Amina Njoya", "amina@demo.example.com", 85000),
        ("Garden 102", 1, "occupied", "Daniel Eko", "daniel@demo.example.com", 90000),
        ("Terrace 201", 2, "occupied", "Lea Martin", "lea@demo.example.com", 110000),
        ("Terrace 202", 2, "available", None, None, 0),
        ("Skyline 301", 3, "occupied", "Samuel Muna", "samuel@demo.example.com", 125000),
        ("Skyline 302", 3, "maintenance", None, None, 0),
    ]
    for index, (name, floor, status, tenant_name, email, rent) in enumerate(homes):
        apartment = Apartment(name=name, floor=floor, status=status)
        db.add(apartment)
        db.flush()
        living = Room(name="Living room", type="living_room", apartment_id=apartment.id)
        bedroom = Room(name="Bedroom", type="bedroom", apartment_id=apartment.id)
        db.add_all([living, bedroom])
        db.flush()
        switch = Device(name="Welcome switch", type="switch", room_id=living.id, is_online=True, is_enabled=True, power="off")
        light = Device(name="Pendant light", type="light", room_id=living.id, is_online=True, is_enabled=True, power="on" if index < 3 else "off")
        fan = Device(name="Ceiling fan", type="fan", room_id=bedroom.id, is_online=index != 4, is_enabled=status != "maintenance", power="off")
        db.add_all([switch, light, fan])
        db.flush()
        if status == "occupied":
            db.add(AutomationRule(name="A warm welcome", apartment_id=apartment.id, source_device_id=switch.id,
                                  source_power="on", target_device_id=light.id, target_power="on", is_enabled=True))
            db.add(AutomationRule(name="Lights out", apartment_id=apartment.id, source_device_id=switch.id,
                                  source_power="off", target_device_id=light.id, target_power="off", is_enabled=True))
        if tenant_name:
            tenant = User(full_name=tenant_name, email=email, password_hash=hash_password(password), role="tenant", apartment_id=apartment.id)
            db.add(tenant)
            db.flush()
            paid = rent if index in (0, 2) else (30000 if index == 1 else 0)
            due = today - timedelta(days=5) if index in (1, 4) else today + timedelta(days=5)
            db.add(RentCharge(tenant_id=tenant.id, apartment_id=apartment.id, period=today.strftime("%Y-%m"),
                              due_date=due, amount_minor=rent, currency="XAF", paid_amount_minor=paid,
                              paid_at=datetime.now(timezone.utc) if paid == rent else None))
            previous = date(today.year, today.month, 1) - timedelta(days=1)
            db.add(RentCharge(tenant_id=tenant.id, apartment_id=apartment.id, period=previous.strftime("%Y-%m"),
                              due_date=previous.replace(day=5), amount_minor=rent, currency="XAF", paid_amount_minor=rent,
                              paid_at=datetime.combine(previous.replace(day=4), datetime.min.time(), tzinfo=timezone.utc)))
    db.commit()
    return True


def main():
    parser = argparse.ArgumentParser(description="Run the Smart Apartment demo on this computer only.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    demo = root / ".demo"
    demo.mkdir(exist_ok=True)
    credential_file = demo / "credentials.json"
    if credential_file.exists():
        credentials = json.loads(credential_file.read_text(encoding="utf-8"))
    else:
        credentials = {"admin_email": "admin@demo.example.com", "tenant_email": "amina@demo.example.com",
                       "password": secrets.token_urlsafe(14), "jwt_secret": secrets.token_urlsafe(48)}
        credential_file.write_text(json.dumps(credentials, indent=2), encoding="utf-8")
    os.environ["DATABASE_URL"] = f"sqlite:///{(demo / 'smart-apartment.db').as_posix()}"
    os.environ["JWT_SECRET_KEY"] = credentials["jwt_secret"]
    from alembic import command
    from alembic.config import Config
    from backend.app.database.connection import SessionLocal
    config = Config(str(root / "alembic.ini"))
    command.upgrade(config, "head")
    with SessionLocal() as db:
        created = seed_demo(db, credentials["password"])
    print("Demo data created." if created else "Existing demo data preserved.", flush=True)
    print(f"Dashboard: http://127.0.0.1:{args.port}/dashboard", flush=True)
    print(f"Demo sign-in details are saved in {credential_file}", flush=True)
    if not args.seed_only:
        import uvicorn
        uvicorn.run("backend.app.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
