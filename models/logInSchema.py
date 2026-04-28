from pydantic import BaseModel
from typing import Optional


class loginSchema(BaseModel):
    email: str
    password: str
    role_id: Optional[str] = None
