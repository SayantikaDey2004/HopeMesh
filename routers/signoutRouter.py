from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordBearer
from app.models.token import Token

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/signout")
def signout(response: Response, token: str = Depends(oauth2_scheme)):
    """
    Sign out the user by removing the token client-side.
    The backend does not need to invalidate JWT (stateless), just instruct frontend to remove token.
    """
    response.delete_cookie(key="access_token")
    return {"message": "Signed out successfully. Redirect to landing page."}
