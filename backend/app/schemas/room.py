from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    type: str = Field(
        min_length=1,
        max_length=50,
    )


class RoomUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    type: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )


class RoomResponse(BaseModel):
    id: int
    name: str
    type: str
    apartment_id: int

    model_config = ConfigDict(from_attributes=True)
