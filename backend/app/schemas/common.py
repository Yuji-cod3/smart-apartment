from pydantic import BaseModel, model_validator


class NonNullUpdate(BaseModel):
    """Omitted fields are unchanged; explicit null cannot erase required columns."""

    @model_validator(mode="before")
    @classmethod
    def reject_null_fields(cls, values):
        if isinstance(values, dict):
            for name in cls.model_fields:
                if name in values and values[name] is None:
                    raise ValueError(f"{name} cannot be null.")
        return values
