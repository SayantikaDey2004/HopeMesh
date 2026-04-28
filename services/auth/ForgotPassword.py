import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from core.config import settings
from db.db import password_reset_tokens_collection, users_collection
from services.email.sendResetPasswordEmail import send_reset_password_email


GENERIC_FORGOT_PASSWORD_RESPONSE = {
    "message": "If this email exists, a reset link has been sent."
}
RESET_TOKEN_TTL_MINUTES = 15


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def forgot_password(data):
    user = await users_collection.find_one({"email": data.email})
    if not user:
        return GENERIC_FORGOT_PASSWORD_RESPONSE

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)

    # Invalidate any previously issued but unused reset tokens for this user.
    await password_reset_tokens_collection.update_many(
        {"user_id": user["_id"], "used_at": None},
        {"$set": {"used_at": now_utc}},
    )

    await password_reset_tokens_collection.insert_one(
        {
            "user_id": user["_id"],
            "token_hash": token_hash,
            "expires_at": expires_at,
            "used_at": None,
            "created_at": now_utc,
        }
    )

    reset_link = f"{settings.reset_password_url}?token={quote(raw_token)}"

    try:
        await send_reset_password_email(data.email, reset_link)
    except RuntimeError:
        # Keep response generic even if provider fails to avoid email enumeration.
        pass

    return GENERIC_FORGOT_PASSWORD_RESPONSE
