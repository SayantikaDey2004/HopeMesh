import asyncio
import json
from typing import Any, Dict, List

from google import genai

from core.config import get_settings


settings = get_settings()
client = genai.Client(api_key=settings.GENAI_API_KEY)


def _default_ai_analysis(description: str = "") -> Dict[str, Any]:
    return {
        "description": description,
        "need_type": "Unknown",
        "urgency": "Unknown",
        "resources": [],
    }


def _safe_json_loads(raw_text: str) -> Dict[str, Any]:
    text = (raw_text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _default_ai_analysis("AI response could not be parsed")

    if not isinstance(data, dict):
        return _default_ai_analysis("AI response format was invalid")

    # Backward compatibility for nested shape: {description, ai_analysis: {...}}
    if "ai_analysis" in data and isinstance(data.get("ai_analysis"), dict):
        nested = data["ai_analysis"]
        resources_raw = nested.get("resources", [])
        if not isinstance(resources_raw, list):
            resources_raw = []

        resources = [
            value.strip()
            for value in resources_raw
            if isinstance(value, str) and value.strip()
        ]

        urgency = str(nested.get("urgency") or "Unknown").strip().title()
        allowed_urgency = {"Low", "Medium", "High", "Critical", "Unknown"}
        if urgency not in allowed_urgency:
            urgency = "Unknown"

        return {
            "description": str(data.get("description") or "").strip(),
            "need_type": str(nested.get("need_type") or "Unknown").strip() or "Unknown",
            "urgency": urgency,
            "resources": list(dict.fromkeys(resources)),
        }

    # Legacy flat support: short_summary/detected_needs/priority_level
    resources_raw = data.get("resources", data.get("detected_needs", []))
    if not isinstance(resources_raw, list):
        resources_raw = []

    resources: List[str] = [
        value.strip() for value in resources_raw if isinstance(value, str) and value.strip()
    ]

    urgency = str(data.get("urgency") or data.get("priority_level") or "Unknown").strip().title()
    allowed_urgency = {"Low", "Medium", "High", "Critical", "Unknown"}
    if urgency not in allowed_urgency:
        urgency = "Unknown"

    return {
        "description": str(data.get("description") or data.get("short_summary") or "").strip(),
        "need_type": str(data.get("need_type") or "Unknown").strip() or "Unknown",
        "urgency": urgency,
        "resources": list(dict.fromkeys(resources)),
    }


def analyze_survey_needs_sync(survey_data: Dict[str, Any]) -> Dict[str, Any]:
    prompt = (
        "You are a need detection assistant for humanitarian surveys. "
        "Read the survey details and generate a real-time assessment. "
        "The description must be written by you from the survey context and not copied blindly. "
        "Return JSON only with this exact shape: "
        "{\"description\": string, \"need_type\": string, \"urgency\": string, \"resources\": string[]}. "
        "Use urgency from: Low, Medium, High, Critical. "
        "resources should be selected from: Food, Water, Medicines, Doctors, Volunteers, Transport, Shelter.\n\n"
        f"Survey payload:\n{json.dumps(survey_data, ensure_ascii=True)}"
    )

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    return _safe_json_loads(getattr(response, "text", ""))


async def analyze_survey_needs(survey_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(analyze_survey_needs_sync, survey_data)
    except Exception:
        return _default_ai_analysis("AI analysis unavailable")
