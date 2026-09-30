from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import NonNullUpdate


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)
    is_online: bool = False
    is_enabled: bool = True


class DeviceUpdate(NonNullUpdate):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    is_online: bool | None = None
    is_enabled: bool | None = None


class DeviceResponse(BaseModel):
    id: int
    name: str
    type: str
    room_id: int
    is_online: bool
    is_enabled: bool
    power: Literal["on", "off"]
    state_updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DeviceControl(BaseModel):
    model_config = ConfigDict(extra="forbid")
    power: Literal["on", "off"]
