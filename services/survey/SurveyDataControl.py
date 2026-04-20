from datetime import datetime, timezone

from app.db.db import survey_data_control_collection


def _serialize_survey_data_control(document):
    return {
        "survey_id": str(document["_id"]),
        "name": document.get("name"),
        "phone_number": document.get("phone_number"),
        "email": document.get("email"),
        "location": document["location"],
        "city_area": document["city_area"],
        "pin_code": document["pin_code"],
        "submitted_by": document["submitted_by"],
        "need_type": document["need_type"],
        "other_need_text": document.get("other_need_text"),
        "description": document["description"],
        "urgency_level": document["urgency_level"],
        "people_affected": document["people_affected"],
        "required_resources": document["required_resources"],
        "time_sensitivity": document["time_sensitivity"],
        "contact_preference": document["contact_preference"],
        "created_at": document["created_at"].isoformat(),
    }


async def create_survey_data_control(data):
    survey_data = data.model_dump()
    survey_data["created_at"] = datetime.now(timezone.utc)

    result = await survey_data_control_collection.insert_one(survey_data)

    return {
        "message": "Survey data control form submitted successfully",
        "survey_id": str(result.inserted_id),
    }


async def get_survey_data_controls(limit: int = 50):
    documents = (
        await survey_data_control_collection.find()
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )

    return {
        "total": len(documents),
        "items": [_serialize_survey_data_control(document) for document in documents],
    }