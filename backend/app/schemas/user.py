from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool
from typing import Literal
from backend.app.schemas.rent import RentBalance

from backend.app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

class UserLogin(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

class ApartmentAssignment(BaseModel):
    apartment_id: int = Field(
        ge=1,
    )

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    apartment_id: int | None

    model_config = ConfigDict(
        from_attributes=True,
    )


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: StrictBool


class TenantStatusResponse(BaseModel):
    user: UserResponse
    tenancy_status: Literal["assigned", "unassigned"]
    rent_balances: list[RentBalance]
