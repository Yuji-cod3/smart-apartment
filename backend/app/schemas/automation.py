from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AutomationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    source_device_id: int = Field(gt=0)
    source_power: Literal["on", "off"]
    target_device_id: int = Field(gt=0)
    target_power: Literal["on", "off"]
    is_enabled: bool = True

    @model_validator(mode="after")
    def distinct_devices(self):
        if self.source_device_id == self.target_device_id:
            raise ValueError("Source and target devices must differ.")
        return self


class AutomationResponse(AutomationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    apartment_id: int


class AutomationResult(BaseModel):
    rule_id: int
    outcome: Literal["applied", "unchanged", "not_matched", "disabled", "unavailable", "conflict"]


class AutomationEvaluation(BaseModel):
    results: list[AutomationResult]
