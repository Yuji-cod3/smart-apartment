from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class RentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: int = Field(gt=0)
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    due_date: date
    amount_minor: int = Field(gt=0, le=2_000_000_000, strict=True)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class RentPayment(BaseModel):
    """Cumulative paid amount, not an increment: retries are idempotent."""
    model_config = ConfigDict(extra="forbid")
    paid_amount_minor: int = Field(ge=0, le=2_000_000_000, strict=True)


class RentResponse(RentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    apartment_id: int
    paid_amount_minor: int
    balance_minor: int
    paid_at: datetime | None
    status: Literal["unpaid", "partial", "paid", "overdue"]


class RentBalance(BaseModel):
    currency: str
    outstanding_minor: int
    overdue_minor: int
