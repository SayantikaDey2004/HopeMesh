import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SurveyDataControlValidationSchema(BaseModel):
    submitted_by: str = Field(..., min_length=1, max_length=128)

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(default=None, min_length=7, max_length=20)
    email: Optional[str] = Field(default=None, min_length=5, max_length=254)

    location: str = Field(..., min_length=3, max_length=300)
    city_area: str = Field(..., min_length=2, max_length=100)
    pin_code: str = Field(..., min_length=4, max_length=10)

    need_type: Literal[
        "Food shortage",
        "Medical help",
        "Shelter",
        "Education",
        "Disaster relief",
        "Other",
    ]
    other_need_text: Optional[str] = Field(default=None, min_length=2, max_length=200)

    description: str = Field(..., min_length=15, max_length=2000)
    urgency_level: Literal["Low", "Medium", "High", "Critical"]
    people_affected: Literal["1-10", "10-50", "50-100", "100+"]

    required_resources: List[
        Literal[
            "Food",
            "Water",
            "Medicines",
            "Doctors",
            "Volunteers",
            "Transport",
            "Shelter",
        ]
    ] = Field(..., min_length=1)

    time_sensitivity: Literal[
        "Immediate (within 24 hrs)",
        "Within 2-3 days",
        "Within a week",
    ]
    contact_preference: Literal["Phone", "Email"]

    @field_validator("name", "phone_number", "email", "other_need_text", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value):
        if value is None:
            return None

        cleaned_value = value.strip()
        if not cleaned_value:
            return None

        return cleaned_value

    @field_validator(
        "submitted_by",
        "location",
        "city_area",
        "pin_code",
        "description",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("This field is required")

        return cleaned_value

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        if not re.match(r"^\+?[0-9]{7,15}$", value):
            raise ValueError("Phone number must contain only digits and optional +")

        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not re.match(email_pattern, value):
            raise ValueError("Email must be a valid email address")

        return value.lower()

    @field_validator("pin_code")
    @classmethod
    def validate_pin_code(cls, value: str) -> str:
        if not re.match(r"^[0-9]{4,10}$", value):
            raise ValueError("Pin code must be 4 to 10 digits")

        return value

    @field_validator("required_resources")
    @classmethod
    def deduplicate_resources(cls, value: List[str]) -> List[str]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_conditional_fields(self):
        if self.need_type == "Other" and not self.other_need_text:
            raise ValueError("other_need_text is required when need_type is Other")

        if self.contact_preference == "Phone" and not self.phone_number:
            raise ValueError("phone_number is required when contact_preference is Phone")

        if self.contact_preference == "Email" and not self.email:
            raise ValueError("email is required when contact_preference is Email")

        return self
