import asyncio
import json
from typing import Any, Dict, List

from google import genai

from app.core.config import get_settings


settings = get_settings()
client = genai.Client(api_key=settings.GENAI_API_KEY)


def _default_ai_output(description: str = "") -> Dict[str, Any]:
    return {
        "description": description,
        "ai_analysis": {
            "need_type": "Unknown",
            "urgency": "Unknown",
            "resources": [],
        },
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
        return _default_ai_output("AI response could not be parsed")

    if not isinstance(data, dict):
        return _default_ai_output("AI response format was invalid")

    # Backward compatibility if model returns previous key format.
    if "ai_analysis" not in data:
        return {
            "description": str(data.get("description") or data.get("short_summary") or "").strip(),
            "ai_analysis": {
                "need_type": str(data.get("need_type") or "Unknown").strip() or "Unknown",
                "urgency": str(data.get("urgency") or data.get("priority_level") or "Unknown").strip().title() or "Unknown",
                "resources": [
                    value.strip()
                    for value in data.get("resources", data.get("detected_needs", []))
                    if isinstance(value, str) and value.strip()
                ],
            },
        }

    ai_analysis = data.get("ai_analysis")
    if not isinstance(ai_analysis, dict):
        return _default_ai_output(str(data.get("description") or "").strip())

    resources_raw = ai_analysis.get("resources")
    if not isinstance(resources_raw, list):
        resources_raw = []

    resources: List[str] = []
    for resource in resources_raw:
        if isinstance(resource, str) and resource.strip():
            resources.append(resource.strip())

    urgency = str(ai_analysis.get("urgency") or "Unknown").strip().title()
    allowed_urgency = {"Low", "Medium", "High", "Critical", "Unknown"}
    if urgency not in allowed_urgency:
        urgency = "Unknown"

    need_type = str(ai_analysis.get("need_type") or "Unknown").strip() or "Unknown"

    return {
        "description": str(data.get("description") or "").strip(),
        "ai_analysis": {
            "need_type": need_type,
            "urgency": urgency,
            "resources": list(dict.fromkeys(resources)),
        },
    }


def analyze_survey_needs_sync(survey_data: Dict[str, Any]) -> Dict[str, Any]:
    prompt = (
        "You are a need detection assistant for humanitarian surveys. "
        "Analyze this payload and return JSON only with this exact shape: "
        "{\"description\": string, \"ai_analysis\": {\"need_type\": string, \"urgency\": string, \"resources\": string[]}}. "
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
        return _default_ai_output("AI analysis unavailable")