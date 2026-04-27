from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional

class VolunteerProfileValidationSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    ngo_id: str = Field(..., description="NGO ID this volunteer is registering with")
    skill: Literal[
        "Food shortage",
        "Medical help",
        "Shelter",
        "Education",
        "Disaster relief",
        "Other",
    ]
    contact_number: str = Field(default="", description="Volunteer contact number")
    location: str = Field(default="", description="Volunteer location")
    user_id: Optional[str] = None
