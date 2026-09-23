from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.apartment import Apartment
from backend.app.schemas.apartment import (
    ApartmentCreate,
    ApartmentResponse,
    ApartmentUpdate,
)


router = APIRouter(
    prefix="/apartments",
    tags=["Apartments"],
)


@router.post(
    "/",
    response_model=ApartmentResponse,
    status_code=201,
)
def create_apartment(
    apartment: ApartmentCreate,
    db: Session = Depends(get_db),
):
    existing_apartment = (
        db.query(Apartment)
        .filter(Apartment.name == apartment.name)
        .first()
    )

    if existing_apartment:
        raise HTTPException(
            status_code=409,
            detail="An apartment with this name already exists.",
        )

    new_apartment = Apartment(
        name=apartment.name,
        floor=apartment.floor,
        status=apartment.status,
    )

    db.add(new_apartment)
    db.commit()
    db.refresh(new_apartment)

    return new_apartment
@router.get(
    "/",
    response_model=list[ApartmentResponse],
)
def get_apartments(
    db: Session = Depends(get_db),
):
    apartments = db.query(Apartment).all()

    return apartments
@router.get(
    "/{apartment_id}",
    response_model=ApartmentResponse,
)
def get_apartment(
    apartment_id: int,
    db: Session = Depends(get_db),
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

    return apartment
@router.patch(
    "/{apartment_id}",
    response_model=ApartmentResponse,
)
def update_apartment(
    apartment_id: int,
    apartment_data: ApartmentUpdate,
    db: Session = Depends(get_db),
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

    update_data = apartment_data.model_dump(
        exclude_unset=True
    )

    if "name" in update_data:
        existing_apartment = (
            db.query(Apartment)
            .filter(
                Apartment.name == update_data["name"],
                Apartment.id != apartment_id,
            )
            .first()
        )

        if existing_apartment:
            raise HTTPException(
                status_code=409,
                detail="An apartment with this name already exists.",
            )

    for field, value in update_data.items():
        setattr(apartment, field, value)

    db.commit()
    db.refresh(apartment)

    return apartment
@router.delete(
    "/{apartment_id}",
    status_code=204,
)
def delete_apartment(
    apartment_id: int,
    db: Session = Depends(get_db),
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

    db.delete(apartment)
    db.commit()

    return None
