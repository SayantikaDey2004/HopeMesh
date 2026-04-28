
from fastapi import HTTPException
import re
from db.db import staff_collection, users_collection, ngo_collection
from core.security import hash_password
from services.auth.user_id import generate_next_ngo_member_id
from Validation.staffProfileValidation import StaffProfileValidationSchema



async def signup_staff(data):
    """Create a new staff member for an NGO."""
    # Validate input data
    validated_data = StaffProfileValidationSchema(**data.dict())
    normalized_email = validated_data.email.strip().lower()

    # Verify NGO exists

    ngo = await ngo_collection.find_one({"ngo_id": validated_data.ngo_id})
    if not ngo:
        raise HTTPException(status_code=400, detail="NGO does not exist")

    # Check if email already exists

    existing = await users_collection.find_one({"email": normalized_email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")


    requested_user_id = str(validated_data.user_id or "").strip().upper()
    if requested_user_id:
        if not re.match(r"^ST_\d{2,}$", requested_user_id):
            raise HTTPException(status_code=400, detail="Invalid staff role ID format")

        existing_user_id = await users_collection.find_one({"user_id": requested_user_id})
        if existing_user_id:
            raise HTTPException(status_code=400, detail="Role ID already exists")

        user_id = requested_user_id
    else:
        user_id = await generate_next_ngo_member_id(ngo_id=validated_data.ngo_id, role="staff")

    # Create staff user

    staff_user = {
        "user_id": user_id,
        "name": validated_data.name,
        "email": normalized_email,
        "password": hash_password(validated_data.password),
        "ngo_id": validated_data.ngo_id,
        "role": "staff",
        "designation": validated_data.designation,
        "contact_number": validated_data.contact_number,
    }

    await users_collection.insert_one(staff_user)

    staff_record = {
        "user_id": user_id,
        "staff_id": user_id,
        "ngo_id": validated_data.ngo_id,
        "name": validated_data.name,
        "email": normalized_email,
        "designation": validated_data.designation,
        "contact_number": validated_data.contact_number,
        "role": "staff",
    }

    await staff_collection.insert_one(staff_record)

    return {
        "message": "Staff member created successfully",
        "user_id": user_id,
        "staff_id": user_id,
        "ngo_id": data.ngo_id,
    }
