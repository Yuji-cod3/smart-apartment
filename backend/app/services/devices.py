from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.device import Device
from backend.app.models.room import Room
from backend.app.models.user import User


CONTROLLABLE_TYPES = {"light", "fan", "switch", "smart_plug", "air_conditioner"}


def require_apartment_access(user: User, apartment_id: int) -> None:
    if user.role != "admin" and user.apartment_id != apartment_id:
        raise HTTPException(403, "Access to this apartment is not permitted.")


def find_device(db: Session, apartment_id: int, room_id: int, device_id: int) -> Device:
    device = db.query(Device).join(Room).filter(
        Device.id == device_id, Device.room_id == room_id,
        Room.apartment_id == apartment_id,
    ).first()
    if device is None:
        raise HTTPException(404, "Device not found.")
    return device


def control_unavailable_reason(device: Device) -> str | None:
    if device.type not in CONTROLLABLE_TYPES:
        return "Device type does not support power control."
    if not device.is_enabled:
        return "Device is disabled."
    if not device.is_online:
        return "Device is offline."
    return None


def set_power(device: Device, power: str) -> bool:
    reason = control_unavailable_reason(device)
    if reason:
        raise HTTPException(409, reason)
    if device.power == power:
        return False
    device.power = power
    device.state_updated_at = datetime.now(timezone.utc)
    return True
