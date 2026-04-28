from jose import JWTError, jwt

from core.config import settings


def verify_reset_password_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as error:
        raise ValueError("Invalid or expired reset token") from error

    if payload.get("type") != "reset_password":
        raise ValueError("Invalid reset token type")

    email = payload.get("sub")
    if not email:
        raise ValueError("Invalid reset token payload")

    return email
