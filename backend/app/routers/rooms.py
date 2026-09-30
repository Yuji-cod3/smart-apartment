from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.apartment import Apartment
from backend.app.models.room import Room
from backend.app.models.user import User
from backend.app.schemas.room import (
    RoomCreate,
    RoomResponse,
    RoomUpdate,
)
from backend.app.services.authorization import require_admin
from backend.app.services.security import get_current_user
from backend.app.services.automation import remove_device_rules


router = APIRouter(
    prefix="/apartments/{apartment_id}/rooms",
    tags=["Rooms"],
)


@router.post(
    "/",
    response_model=RoomResponse,
    status_code=201,
)
def create_room(
    apartment_id: int,
    room: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    apartment = (
        db.query(Apartment)
        .filter(Apartment.id == apartment_id)
        .first()
    )

    if apartment is None:
        raise HTTPException(
            status_code=404,
            detail="Apartment not found.",
        )

    new_room = Room(
        name=room.name,
        type=room.type,
        apartment_id=apartment_id,
    )

    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return new_room


@router.get(
    "/",
    response_model=list[RoomResponse],
)
def get_rooms(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apartment = (
        db.query(Apartment)
        .filter(Apartment.id == apartment_id)
        .first()
    )

    if apartment is None:
        raise HTTPException(
            status_code=404,
            detail="Apartment not found.",
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
        db.query(Room)
        .filter(Room.apartment_id == apartment_id)
        .all()
    )


@router.get(
    "/{room_id}",
    response_model=RoomResponse,
)
def get_room(
    apartment_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    if (
        current_user.role != "admin"
        and current_user.apartment_id != apartment_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access to this apartment is not permitted.",
        )

    return room


@router.patch(
    "/{room_id}",
    response_model=RoomResponse,
)
def update_room(
    apartment_id: int,
    room_id: int,
    room_data: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
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

    update_data = room_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(room, field, value)

    db.commit()
    db.refresh(room)

    return room


@router.delete(
    "/{room_id}",
    status_code=204,
)
def delete_room(
    apartment_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
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

    remove_device_rules(db, [device.id for device in room.devices])
    db.delete(room)
    db.commit()

    return None
