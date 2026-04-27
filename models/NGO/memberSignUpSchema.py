from typing import Literal, Optional

from pydantic import BaseModel, Field


class NgoMemberSignUpSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    ngo_id: str = Field(..., min_length=1)
    identity_type: Literal["staff", "volunteer"]
    role_id: Optional[str] = None
    skill: Optional[
        Literal[
            "Food shortage",
            "Medical help",
            "Shelter",
            "Education",
            "Disaster relief",
            "Other",
        ]
    ] = None
    designation: str = Field(default="Staff")
    contact_number: str = Field(default="")
    location: str = Field(default="")