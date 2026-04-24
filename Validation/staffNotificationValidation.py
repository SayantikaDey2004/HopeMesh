from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class StaffNotificationListValidationSchema(BaseModel):
    task_status: Optional[Literal["pending", "accepted", "rejected"]] = None
    event_type: Optional[Literal["assigned", "status_changed"]] = None
    limit: int = Field(default=50, ge=1, le=200)

    @field_validator("task_status", "event_type", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value):
        if value is None:
            return None

        cleaned_value = str(value).strip().lower()
        if not cleaned_value:
            return None

        return cleaned_value
