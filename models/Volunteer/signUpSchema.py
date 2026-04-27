from pydantic import BaseModel, Field
from typing import Literal, Optional


class VolunteerSignUpSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    ngo_id: str = Field(..., description="NGO ID this volunteer is registering with")
    skill: Literal[
        "Food shortage",
        "Medical help",
        "Shelter",
        "Education",
        "Disaster relief",
        "Other",
    ] = Field(..., description="Volunteer's primary skill")
    contact_number: str = Field(default="", description="Volunteer contact number")
    location: str = Field(default="", description="Volunteer location")
    user_id: Optional[str] = None
