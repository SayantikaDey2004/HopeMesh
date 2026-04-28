from fastapi import HTTPException
from db.db import users_collection
from core.security import hash_password
from services.auth.user_id import generate_next_user_id


# -------- USER SIGNUP --------
async def signup_user(data):

    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user_id = await generate_next_user_id(role="User")

    user = {
        "user_id": user_id,
        "name": data.name,
        "email": data.email,
        "skill": data.skill,
        "password": hash_password(data.password),
        "role": "volunteer",
    }

    await users_collection.insert_one(user)

    return {
        "message": "User created successfully",
        "user_id": user_id,
    }
