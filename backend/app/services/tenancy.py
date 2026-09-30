from sqlalchemy.orm import Session

from backend.app.models.apartment import Apartment
from backend.app.models.user import User


def sync_occupancy(db: Session, apartment_id: int | None) -> None:
    if apartment_id is None:
        return
    db.flush()
    apartment = db.get(Apartment, apartment_id)
    if apartment is None or apartment.status == "maintenance":
        return
    occupied = db.query(User).filter(User.apartment_id == apartment_id, User.role == "tenant").first()
    apartment.status = "occupied" if occupied else "available"
