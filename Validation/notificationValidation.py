from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class VolunteerNotificationListValidationSchema(BaseModel):
    task_status: Optional[Literal["pending", "accepted", "rejected"]] = None
    limit: int = Field(default=50, ge=1, le=200)


class VolunteerNotificationStatusUpdateValidationSchema(BaseModel):
    task_status: Literal["pending", "accepted", "rejected"]

    @field_validator("task_status", mode="before")
    @classmethod
    def normalize_task_status(cls, value):
        cleaned_value = str(value or "").strip().lower()
        if cleaned_value not in {"pending", "accepted", "rejected"}:
            raise ValueError("task_status must be pending, accepted, or rejected")

        return cleaned_value
