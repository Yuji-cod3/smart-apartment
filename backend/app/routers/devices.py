from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.device import Device
from backend.app.models.room import Room
from backend.app.models.user import User
from backend.app.schemas.device import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    DeviceControl,
)
from backend.app.services.authorization import require_admin
from backend.app.services.security import get_current_user
from backend.app.services.devices import find_device, require_apartment_access, set_power
from backend.app.services.automation import evaluate_rules, remove_device_rules


router = APIRouter(
    prefix="/apartments/{apartment_id}/rooms/{room_id}/devices",
    tags=["Devices"],
)


def get_room_or_404(
    apartment_id: int,
    room_id: int,
    db: Session,
) -> Room:
    room = (
        db.query(Room)
        .filter(
            Room.id == room_id,
            Room.apartment_id == apartment_id,
        )
        .first()
    )

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found.",
        )

    return room


@router.post(
    "/",
    response_model=DeviceResponse,
    status_code=201,
)
def create_device(
    apartment_id: int,
    room_id: int,
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    room = get_room_or_404(
        apartment_id,
        room_id,
        db,
    )

    new_device = Device(
        name=device.name,
        type=device.type,
        room_id=room.id,
        is_online=device.is_online,
        is_enabled=device.is_enabled,
    )

    db.add(new_device)
    db.commit()
    db.refresh(new_device)

    return new_device


@router.get(
    "/",
    response_model=list[DeviceResponse],
)
def get_devices(
    apartment_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = get_room_or_404(
        apartment_id,
        room_id,
        db,
    )

    if (
        current_user.role != "admin"
        and current_user.apartment_id != apartment_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access to this apartment is not permitted.",
        )

    return (
        db.query(Device)
        .filter(Device.room_id == room.id)
        .all()
    )


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
)
def get_device(
    apartment_id: int,
    room_id: int,
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = (
        db.query(Device)
        .join(Room)
        .filter(
            Device.id == device_id,
            Device.room_id == room_id,
            Room.id == room_id,
            Room.apartment_id == apartment_id,
        )
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found.",
        )

    if (
        current_user.role != "admin"
        and current_user.apartment_id != apartment_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access to this apartment is not permitted.",
        )

    return device


@router.patch(
    "/{device_id}",
    response_model=DeviceResponse,
)
def update_device(
    apartment_id: int,
    room_id: int,
    device_id: int,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = (
        db.query(Device)
        .join(Room)
        .filter(
            Device.id == device_id,
            Device.room_id == room_id,
            Room.id == room_id,
            Room.apartment_id == apartment_id,
        )
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found.",
        )

    update_data = device_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(device, field, value)

    db.commit()
    db.refresh(device)

    return device


@router.delete(
    "/{device_id}",
    status_code=204,
)
def delete_device(
    apartment_id: int,
    room_id: int,
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    device = (
        db.query(Device)
        .join(Room)
        .filter(
            Device.id == device_id,
            Device.room_id == room_id,
            Room.id == room_id,
            Room.apartment_id == apartment_id,
        )
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found.",
        )

    remove_device_rules(db, [device.id])
    db.delete(device)
    db.commit()

    return None


@router.get("/{device_id}/state", response_model=DeviceResponse)
def get_device_state(
    apartment_id: int, room_id: int, device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = find_device(db, apartment_id, room_id, device_id)
    require_apartment_access(current_user, apartment_id)
    return device


@router.put("/{device_id}/state", response_model=DeviceResponse)
def control_device(
    apartment_id: int, room_id: int, device_id: int, command: DeviceControl,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = find_device(db, apartment_id, room_id, device_id)
    require_apartment_access(current_user, apartment_id)
    set_power(device, command.power)
    evaluate_rules(db, apartment_id, source_device_id=device.id)
    db.commit()
    db.refresh(device)
    return device
