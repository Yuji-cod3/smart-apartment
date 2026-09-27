from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.connection import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    apartment_id: Mapped[int] = mapped_column(
        ForeignKey("apartments.id"),
        nullable=False,
    )

    apartment = relationship(
        "Apartment",
        back_populates="rooms",
    )
    devices = relationship(
        "Device",
        back_populates="room",
        cascade="all, delete-orphan",
    )
