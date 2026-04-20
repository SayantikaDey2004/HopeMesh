from datetime import datetime, timezone

from app.db.db import survey_data_control_collection
from app.services.ai import analyze_survey_needs


def _normalize_ai_need_output(ai_need_output):
    default_output = {
        "description": "AI analysis unavailable",
        "ai_analysis": {
            "need_type": "Unknown",
            "urgency": "Unknown",
            "resources": [],
        },
    }

    if not isinstance(ai_need_output, dict):
        return default_output

    if "ai_analysis" in ai_need_output and isinstance(ai_need_output.get("ai_analysis"), dict):
        ai_analysis = ai_need_output["ai_analysis"]
        resources = ai_analysis.get("resources", [])
        if not isinstance(resources, list):
            resources = []

        return {
            "description": str(ai_need_output.get("description") or "").strip(),
            "ai_analysis": {
                "need_type": str(ai_analysis.get("need_type") or "Unknown").strip() or "Unknown",
                "urgency": str(ai_analysis.get("urgency") or "Unknown").strip().title() or "Unknown",
                "resources": [
                    item.strip() for item in resources if isinstance(item, str) and item.strip()
                ],
            },
        }

    # Legacy shape support: short_summary/detected_needs/priority_level
    resources = ai_need_output.get("resources", ai_need_output.get("detected_needs", []))
    if not isinstance(resources, list):
        resources = []

    return {
        "description": str(
            ai_need_output.get("description") or ai_need_output.get("short_summary") or ""
        ).strip(),
        "ai_analysis": {
            "need_type": str(ai_need_output.get("need_type") or "Unknown").strip() or "Unknown",
            "urgency": str(
                ai_need_output.get("urgency") or ai_need_output.get("priority_level") or "Unknown"
            ).strip().title() or "Unknown",
            "resources": [
                item.strip() for item in resources if isinstance(item, str) and item.strip()
            ],
        },
    }


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
        "ai_need_output": _normalize_ai_need_output(document.get("ai_need_output")),
        "created_at": document["created_at"].isoformat(),
    }


async def create_survey_data_control(data):
    survey_data = data.model_dump()
    survey_data["ai_need_output"] = await analyze_survey_needs(survey_data)
    survey_data["created_at"] = datetime.now(timezone.utc)

    result = await survey_data_control_collection.insert_one(survey_data)

    return {
        "message": "Survey data control form submitted successfully",
        "survey_id": str(result.inserted_id),
        "ai_need_output": survey_data["ai_need_output"],
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