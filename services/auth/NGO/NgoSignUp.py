
from fastapi import HTTPException
import re

from db.db import users_collection, ngo_collection
from core.security import hash_password
from services.auth.user_id import generate_next_user_id
from Validation.ngoProfileValidation import NGOProfileValidationSchema


def _build_ngo_id_prefix(name: str) -> str:
    normalized_name = re.sub(r"\s+", "_", name.strip())
    normalized_name = re.sub(r"[^A-Za-z0-9_]", "", normalized_name)
    normalized_name = re.sub(r"_+", "_", normalized_name).strip("_")
    return normalized_name or "NGO"


async def _generate_next_ngo_id(name: str) -> str:
    prefix = _build_ngo_id_prefix(name)
    id_pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$", re.IGNORECASE)

    existing_ngos = await ngo_collection.find(
        {"ngo_id": {"$regex": rf"^{re.escape(prefix)}_\d+$", "$options": "i"}}
    ).to_list(length=10000)

    max_number = 0
    for ngo in existing_ngos:
        current_ngo_id = str(ngo.get("ngo_id") or "")
        matched = id_pattern.match(current_ngo_id)
        if matched:
            max_number = max(max_number, int(matched.group(1)))

    return f"{prefix}_{max_number + 1:02d}"



async def signup_ngo(data):
    # Validate input data
    validated_data = NGOProfileValidationSchema(**data.dict())
    normalized_email = validated_data.email.strip().lower()


    existing = await users_collection.find_one({"email": normalized_email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")


    user_id = await generate_next_user_id(role="NGO")

    # 1. create user (admin)

    user = {
        "user_id": user_id,
        "name": validated_data.name,
        "email": normalized_email,
        "password": hash_password(validated_data.password),
        "role": "ngo_admin",
    }

    user_result = await users_collection.insert_one(user)
    admin_db_id = str(user_result.inserted_id)

    ngo_id = await _generate_next_ngo_id(validated_data.name)

    # 2. create NGO with admin_id

    ngo = {
        "name": validated_data.name,
        "address": validated_data.address,
        "description": validated_data.description,
        "admin_id": admin_db_id,
        "admin_user_id": user_id,
        "ngo_id": ngo_id,
    }

    await ngo_collection.insert_one(ngo)

    return {
        "message": "NGO created with admin",
        "ngo_id": ngo_id,
        "user_id": user_id,
    }
