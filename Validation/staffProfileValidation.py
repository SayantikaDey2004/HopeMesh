from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class StaffProfileValidationSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    ngo_id: str = Field(..., description="NGO ID this staff belongs to")
    designation: str = Field(default="Staff", description="Staff designation/role")
    contact_number: str = Field(default="", description="Staff contact number")
    user_id: Optional[str] = None
