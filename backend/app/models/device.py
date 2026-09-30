from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.connection import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (CheckConstraint("power IN ('on', 'off')", name="ck_device_power"),)

    power: Mapped[str] = mapped_column(String(3), default="off", server_default="off")
    state_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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

    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"),
        nullable=False,
    )

    is_online: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    room = relationship(
        "Room",
        back_populates="devices",
    )
