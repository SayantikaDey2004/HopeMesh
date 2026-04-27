from pydantic import BaseModel, Field
from typing import Optional


class StaffSignUpSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    ngo_id: str = Field(..., description="NGO ID this staff belongs to")
    designation: str = Field(default="Staff", description="Staff designation/role")
    contact_number: str = Field(default="", description="Staff contact number")
    user_id: Optional[str] = None
