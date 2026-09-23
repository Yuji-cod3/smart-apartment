from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ApartmentStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class ApartmentCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
    )

    floor: int = Field(
        ge=0,
        le=100,
    )

    status: ApartmentStatus = ApartmentStatus.AVAILABLE


class ApartmentUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    floor: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    status: ApartmentStatus | None = None


class ApartmentResponse(BaseModel):
    id: int
    name: str
    floor: int
    status: ApartmentStatus

    model_config = ConfigDict(from_attributes=True)
