from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    __table_args__ = (
        CheckConstraint("source_power IN ('on', 'off')", name="ck_rule_source_power"),
        CheckConstraint("target_power IN ('on', 'off')", name="ck_rule_target_power"),
        CheckConstraint("source_device_id != target_device_id", name="ck_rule_distinct_devices"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    apartment_id: Mapped[int] = mapped_column(ForeignKey("apartments.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    source_device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    source_power: Mapped[str] = mapped_column(String(3))
    target_device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    target_power: Mapped[str] = mapped_column(String(3))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
