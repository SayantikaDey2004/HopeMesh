from pydantic import BaseModel

class SignOutSchema(BaseModel):
    message: str = "Signed out successfully. Redirect to landing page."
