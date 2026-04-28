from fastapi import HTTPException
import re
from db.db import users_collection
from core.security import verify_password, create_access_token


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def _requires_role_id(user: dict) -> bool:
    role = _normalize_text(user.get("role")).lower()
    ngo_id = _normalize_text(user.get("ngo_id") or user.get("ngoId"))
    return role in {"staff", "volunteer"} and bool(ngo_id)


async def login_user(data):

    normalized_identifier = _normalize_text(data.email)
    normalized_email = normalized_identifier.lower()
    provided_role_id = _normalize_text(getattr(data, "role_id", None))

    user = await users_collection.find_one({
        "$or": [
            {
                "email": {
                    "$regex": f"^{re.escape(normalized_email)}$",
                    "$options": "i",
                }
            },
            {
                "user_id": {
                    "$regex": f"^{re.escape(normalized_identifier)}$",
                    "$options": "i",
                }
            },
        ]
    })

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if _requires_role_id(user):
        stored_role_id = _normalize_text(user.get("user_id"))
        if not provided_role_id or provided_role_id.lower() != stored_role_id.lower():
            raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({
        "user_id": str(user["_id"]),
        "email": user["email"]
    })

    return {"access_token": token}
