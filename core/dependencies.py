from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from bson import ObjectId

from app.core.config import settings
from app.db.db import membership_collection, ngo_collection, users_collection

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from error

    user_id = str(payload.get("user_id") or "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token payload",
        )

    return {
        "user_id": user_id,
        "email": str(payload.get("email") or "").strip().lower(),
    }


def _extract_ngo_id(document: dict | None) -> str:
    if not isinstance(document, dict):
        return ""

    for key in ("ngo_id", "ngoId", "organization_id", "organizationId"):
        value = str(document.get(key) or "").strip()
        if value:
            return value

    return ""


def _parse_object_id(value: str) -> ObjectId | None:
    if ObjectId.is_valid(value):
        return ObjectId(value)
    return None


async def _resolve_current_ngo_id(
    payload: dict,
    selected_ngo_id: str | None = None,
) -> str:
    user_id = payload["user_id"]
    user_object_id = _parse_object_id(user_id)
    requested_ngo_id = str(selected_ngo_id or "").strip()

    accessible_ngo_ids: set[str] = set()

    admin_filters = [{"admin_id": user_id}]
    if user_object_id:
        admin_filters.append({"admin_id": user_object_id})

    admin_ngos = await ngo_collection.find(
        {"$or": admin_filters},
        {"ngo_id": 1, "ngoId": 1, "organization_id": 1, "organizationId": 1},
    ).to_list(length=200)
    for admin_ngo in admin_ngos:
        ngo_id = _extract_ngo_id(admin_ngo)
        if ngo_id:
            accessible_ngo_ids.add(ngo_id)

    user_filters = [{"_id": user_id}]
    if user_object_id:
        user_filters.append({"_id": user_object_id})

    user = await users_collection.find_one(
        {"$or": user_filters},
        {"ngo_id": 1, "ngoId": 1, "organization_id": 1, "organizationId": 1},
    )
    ngo_id = _extract_ngo_id(user)
    if ngo_id:
        accessible_ngo_ids.add(ngo_id)

    membership_user_filters = [{"user_id": user_id}, {"userId": user_id}]
    if user_object_id:
        membership_user_filters.extend(
            [{"user_id": user_object_id}, {"userId": user_object_id}]
        )

    memberships = await membership_collection.find(
        {
            "$and": [
                {"$or": membership_user_filters},
                {"status": {"$nin": ["inactive", "removed"]}},
                {"is_active": {"$ne": False}},
            ]
        },
        {
            "ngo_id": 1,
            "ngoId": 1,
            "organization_id": 1,
            "organizationId": 1,
        },
    ).to_list(length=500)
    for membership in memberships:
        ngo_id = _extract_ngo_id(membership)
        if ngo_id:
            accessible_ngo_ids.add(ngo_id)

    if not accessible_ngo_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user is not linked to any NGO",
        )

    if requested_ngo_id:
        if requested_ngo_id not in accessible_ngo_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Requested NGO is not accessible for this user",
            )

        return requested_ngo_id

    if len(accessible_ngo_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple NGOs found for user. Set X-NGO-ID header",
        )

    return next(iter(accessible_ngo_ids))


async def get_current_ngo_id(
    payload: dict = Depends(get_current_token_payload),
    selected_ngo_id: str | None = Header(default=None, alias="X-NGO-ID"),
) -> str:
    return await _resolve_current_ngo_id(payload, selected_ngo_id)