from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class RentCharge(Base):
    __tablename__ = "rent_charges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "period", name="uq_rent_tenant_period"),
        CheckConstraint("amount_minor > 0", name="ck_rent_amount"),
        CheckConstraint("paid_amount_minor >= 0 AND paid_amount_minor <= amount_minor", name="ck_rent_paid"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    apartment_id: Mapped[int] = mapped_column(ForeignKey("apartments.id"), index=True)
    period: Mapped[str] = mapped_column(String(7))
    due_date: Mapped[date] = mapped_column(Date)
    amount_minor: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3))
    paid_amount_minor: Mapped[int] = mapped_column(default=0, server_default="0")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
