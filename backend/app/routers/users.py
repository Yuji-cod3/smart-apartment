from fastapi import APIRouter, Depends, HTTPException
from backend.app.services.authorization import require_admin
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.apartment import Apartment
from backend.app.models.user import User
from backend.app.schemas.user import (
    ApartmentAssignment,
    UserCreate,
    UserLogin,
    UserResponse,
    UserStatusUpdate,
    TenantStatusResponse,
)
from backend.app.services.auth import hash_password, verify_password
from backend.app.services.jwt import create_access_token
from backend.app.services.security import get_current_user
from backend.app.services.tenancy import sync_occupancy
from backend.app.services.rent import rent_balances
from backend.app.models.rent import RentCharge


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="A user with this email already exists.",
        )

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
@router.post("/login")
def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == login_data.email)
        .first()
    )

    if not user or not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive.",
        )

    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
@router.get(
    "/",
    response_model=list[UserResponse],
)
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(User).all()
@router.put(
    "/{user_id}/apartment",
    response_model=UserResponse,
)
def assign_apartment(
    user_id: int,
    assignment: ApartmentAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    apartment = (
        db.query(Apartment)
        .filter(Apartment.id == assignment.apartment_id)
        .first()
    )

    if apartment is None:
        raise HTTPException(
            status_code=404,
            detail="Apartment not found.",
        )

    if user.role != "tenant":
        raise HTTPException(
            status_code=400,
            detail="Only tenant users can be assigned to apartments.",
        )

    if not user.is_active:
        raise HTTPException(409, "Inactive tenants cannot be assigned to apartments.")
    if apartment.status == "maintenance":
        raise HTTPException(409, "Apartment is under maintenance.")
    previous_apartment_id = user.apartment_id
    user.apartment_id = apartment.id
    sync_occupancy(db, previous_apartment_id)
    sync_occupancy(db, apartment.id)

    db.commit()
    db.refresh(user)

    return user
@router.delete(
    "/{user_id}/apartment",
    response_model=UserResponse,
)
def remove_apartment_assignment(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    if user.role != "tenant":
        raise HTTPException(
            status_code=400,
            detail="Only tenant users can have apartment assignments removed.",
        )

    if user.apartment_id is None:
        raise HTTPException(
            status_code=400,
            detail="Tenant is not assigned to an apartment.",
        )

    previous_apartment_id = user.apartment_id
    user.apartment_id = None
    sync_occupancy(db, previous_apartment_id)

    db.commit()
    db.refresh(user)

    return user


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int, data: UserStatusUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found.")
    if user.role != "tenant":
        raise HTTPException(409, "This endpoint manages tenant accounts only.")
    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/tenant-status", response_model=TenantStatusResponse)
def get_tenant_status(
    user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(403, "Access to this tenant is not permitted.")
    user = db.get(User, user_id)
    if user is None or user.role != "tenant":
        raise HTTPException(404, "Tenant not found.")
    return {
        "user": user,
        "tenancy_status": "assigned" if user.apartment_id is not None else "unassigned",
        "rent_balances": rent_balances(db.query(RentCharge).filter_by(tenant_id=user.id).all()),
    }
