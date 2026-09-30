"""Create an initial admin locally: python -m backend.app.create_admin."""
import argparse
from getpass import getpass

from backend.app.database.connection import SessionLocal
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate
from backend.app.services.auth import hash_password


def create_admin(db, data: UserCreate):
    if db.query(User).filter(User.email == data.email).first():
        raise ValueError("An account with this email already exists; no account was changed.")
    user = User(full_name=data.full_name, email=data.email, password_hash=hash_password(data.password), role="admin")
    db.add(user)
    db.commit()
    return user


def main():
    parser = argparse.ArgumentParser(description="Create an administrator after running Alembic migrations.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()
    password = getpass("Password: ")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match.")
    try:
        data = UserCreate(full_name=args.full_name, email=args.email, password=password)
        with SessionLocal() as db:
            create_admin(db, data)
    except ValueError as error:
        parser.error(str(error))
    print("Administrator created.")


if __name__ == "__main__":
    main()
