from datetime import datetime, timedelta

from jose import jwt

from core.config import settings


RESET_TOKEN_EXPIRE_MINUTES = 30


def get_reset_password_token(email: str) -> str:
    payload = {
        "sub": email,
        "type": "reset_password",
        "exp": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
