import re
import json
import asyncio
from typing import List

from db.db import users_collection
from services.ai import client


_ROLE_ID_PREFIX_MAP = {
    "staff": "ST",
    "volunteer": "VN",
}


def _extract_max_suffix(existing_ids: List[str], prefix: str) -> int:
    id_pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$", re.IGNORECASE)
    max_number = 0

    for current_id in existing_ids:
        matched = id_pattern.match(str(current_id or "").strip())
        if matched:
            max_number = max(max_number, int(matched.group(1)))

    return max_number


def _build_default_role_id(prefix: str, sequence: int) -> str:
    return f"{prefix}_{sequence:02d}"


def _generate_role_id_with_gemini_sync(
    *,
    ngo_id: str,
    role: str,
    prefix: str,
    next_sequence: int,
    existing_ids: List[str],
) -> str:
    prompt = (
        "You generate one unique NGO member ID. "
        "Return JSON only with this exact shape: {\"user_id\": string}. "
        f"Role is '{role}' and NGO is '{ngo_id}'. "
        f"Prefix must be '{prefix}'. "
        f"Suggested next sequence number is {next_sequence}. "
        "Use format PREFIX_XX with at least 2 digits. "
        "Never use any ID from existing IDs.\n\n"
        f"Existing IDs: {json.dumps(existing_ids, ensure_ascii=True)}"
    )

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )

    raw_text = str(getattr(response, "text", "") or "").strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if len(lines) >= 3:
            raw_text = "\n".join(lines[1:-1]).strip()

    parsed = json.loads(raw_text)
    candidate = str(parsed.get("user_id") or "").strip()
    if not candidate:
        raise ValueError("Gemini returned empty user_id")

    id_pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{2,}})$", re.IGNORECASE)
    matched = id_pattern.match(candidate)
    if not matched:
        raise ValueError("Gemini returned invalid ID format")

    candidate_sequence = int(matched.group(1))
    if candidate_sequence != next_sequence:
        raise ValueError("Gemini returned non-sequential ID")

    candidate_upper = candidate.upper()
    existing_upper = {str(item).upper() for item in existing_ids}
    if candidate_upper in existing_upper:
        raise ValueError("Gemini returned duplicate ID")

    return candidate_upper


async def generate_next_user_id(role: str = "User") -> str:
    """Generate next unique ID for a user based on role (User, Staff, Volunteer, NGO)."""
    id_pattern = re.compile(rf"^{re.escape(role)}_(\d+)$", re.IGNORECASE)

    existing_users = await users_collection.find(
        {"user_id": {"$regex": rf"^{re.escape(role)}_\d+$", "$options": "i"}}
    ).to_list(length=100000)

    max_number = 0
    for user in existing_users:
        current_user_id = str(user.get("user_id") or "")
        matched = id_pattern.match(current_user_id)
        if matched:
            max_number = max(max_number, int(matched.group(1)))

    return f"{role}_{max_number + 1:02d}"


async def generate_next_ngo_member_id(ngo_id: str, role: str) -> str:
    normalized_ngo_id = str(ngo_id or "").strip()
    normalized_role = str(role or "").strip().lower()

    if not normalized_ngo_id:
        raise ValueError("ngo_id is required for NGO member ID generation")

    if normalized_role not in _ROLE_ID_PREFIX_MAP:
        raise ValueError("role must be either 'staff' or 'volunteer'")

    prefix = _ROLE_ID_PREFIX_MAP[normalized_role]

    existing_member_documents = await users_collection.find(
        {
            "$and": [
                {"ngo_id": normalized_ngo_id},
                {"role": normalized_role},
                {
                    "user_id": {
                        "$regex": rf"^{re.escape(prefix)}_\d+$",
                        "$options": "i",
                    }
                },
            ]
        },
        {"user_id": 1},
    ).to_list(length=100000)

    existing_ids = [str(item.get("user_id") or "").strip() for item in existing_member_documents]
    existing_ids = [item for item in existing_ids if item]

    next_sequence = _extract_max_suffix(existing_ids, prefix) + 1
    default_id = _build_default_role_id(prefix, next_sequence)

    try:
        generated_id = await asyncio.to_thread(
            _generate_role_id_with_gemini_sync,
            ngo_id=normalized_ngo_id,
            role=normalized_role,
            prefix=prefix,
            next_sequence=next_sequence,
            existing_ids=existing_ids,
        )
        return generated_id
    except Exception:
        return default_id
