
from fastapi import HTTPException
from app.db.db import users_collection, ngo_collection, volunteers_collection
from app.core.security import hash_password
from app.services.auth.user_id import generate_next_ngo_member_id
from Validation.volunteerProfileValidation import VolunteerProfileValidationSchema



async def signup_volunteer(data):
    """Create a new volunteer for an NGO."""
    # Validate input data
    validated_data = VolunteerProfileValidationSchema(**data.dict())
    normalized_email = validated_data.email.strip().lower()

    # Verify NGO exists

    ngo = await ngo_collection.find_one({"ngo_id": validated_data.ngo_id})
    if not ngo:
        raise HTTPException(status_code=400, detail="NGO does not exist")

    # Check if email already exists

    existing = await users_collection.find_one({"email": normalized_email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")


    user_id = await generate_next_ngo_member_id(ngo_id=validated_data.ngo_id, role="volunteer")

    # Create volunteer user

    volunteer_user = {
        "user_id": user_id,
        "name": validated_data.name,
        "email": normalized_email,
        "password": hash_password(validated_data.password),
        "ngo_id": validated_data.ngo_id,
        "role": "volunteer",
        "skill": validated_data.skill,
        "contact_number": validated_data.contact_number,
        "location": validated_data.location,
    }

    await users_collection.insert_one(volunteer_user)

    # Also add to volunteers collection for matching purposes

    volunteer_record = {
        "user_id": user_id,
        "volunteer_id": user_id,
        "ngo_id": validated_data.ngo_id,
        "name": validated_data.name,
        "email": normalized_email,
        "skill": validated_data.skill,
        "contact_number": validated_data.contact_number,
        "location": validated_data.location,
    }

    await volunteers_collection.insert_one(volunteer_record)

    return {
        "message": "Volunteer created successfully",
        "user_id": user_id,
        "volunteer_id": user_id,
        "ngo_id": data.ngo_id,
    }
