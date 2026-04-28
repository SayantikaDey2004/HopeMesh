import hashlib
from datetime import datetime, timezone

from fastapi import HTTPException

from core.security import hash_password
from db.db import password_reset_tokens_collection, users_collection


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def _get_valid_reset_token_row(token_hash: str):
    now_utc = datetime.now(timezone.utc)
    return await password_reset_tokens_collection.find_one(
        {
            "token_hash": token_hash,
            "used_at": None,
            "expires_at": {"$gt": now_utc},
        }
    )


async def reset_password(data):
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    token_hash = _hash_token(data.token)
    token_row = await _get_valid_reset_token_row(token_hash)
    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    now_utc = datetime.now(timezone.utc)
    user_id = token_row["user_id"]

    user = await users_collection.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "password": hash_password(data.new_password),
                "password_changed_at": now_utc,
                "session_invalid_before": now_utc,
            }
        },
    )

    await password_reset_tokens_collection.update_one(
        {"_id": token_row["_id"]},
        {"$set": {"used_at": now_utc}},
    )

    return {"message": "Password reset successful"}


async def validate_reset_password_token(token: str):
    token_hash = _hash_token(token)
    token_row = await _get_valid_reset_token_row(token_hash)
    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    return {"message": "Token is valid"}
