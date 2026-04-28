import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from core.websocketConfig import manager
from db.db import membership_collection, staff_notifications_collection, users_collection

_ALLOWED_URGENCY = {"Low", "Medium", "High", "Critical", "Unknown"}
_ALLOWED_TASK_STATUS = {"pending", "accepted", "rejected"}
_ALLOWED_EVENT_TYPES = {"assigned", "status_changed"}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_urgency(value: Any) -> str:
    urgency = _normalize_text(value).title()
    if urgency not in _ALLOWED_URGENCY:
        return "Unknown"
    return urgency


def _extract_role(document: Dict[str, Any]) -> str:
    if not isinstance(document, dict):
        return ""

    role = _normalize_text(
        document.get("role")
        or document.get("user_role")
        or document.get("account_role")
        or document.get("member_role")
        or document.get("membership_role")
        or document.get("type")
        or document.get("designation")
    ).lower()
    return role


def _is_staff_role(role: str) -> bool:
    normalized_role = _normalize_text(role).lower()
    if not normalized_role:
        return False

    return "staff" in normalized_role


def _extract_ngo_id(document: Dict[str, Any]) -> str:
    if not isinstance(document, dict):
        return ""

    for key in ("ngo_id", "ngoId", "organization_id", "organizationId"):
        value = _normalize_text(document.get(key))
        if value:
            return value

    return ""


def _extract_user_id(document: Dict[str, Any]) -> str:
    if not isinstance(document, dict):
        return ""

    for key in ("user_id", "userId", "member_id", "memberId", "_id"):
        value = _normalize_text(document.get(key))
        if value:
            return value

    return ""


def _is_active_membership(document: Dict[str, Any]) -> bool:
    status = _normalize_text(document.get("status") or "active").lower()
    if status in {"inactive", "removed"}:
        return False

    if document.get("is_active") is False:
        return False

    return True


def _serialize_staff_notification(document: Dict[str, Any]) -> Dict[str, Any]:
    created_at = document.get("created_at")

    task_status = _normalize_text(document.get("task_status")).lower()
    if task_status not in _ALLOWED_TASK_STATUS:
        task_status = "pending"

    event_type = _normalize_text(document.get("event_type")).lower()
    if event_type not in _ALLOWED_EVENT_TYPES:
        event_type = "assigned"

    return {
        "staff_notification_id": _normalize_text(document.get("_id") or document.get("staff_notification_id")),
        "ngo_id": _normalize_text(document.get("ngo_id")),
        "recipient_user_id": _normalize_text(document.get("recipient_user_id")),
        "need_id": _normalize_text(document.get("need_id")),
        "need_type": _normalize_text(document.get("need_type")) or "Unknown",
        "urgency": _normalize_urgency(document.get("urgency")),
        "volunteer_id": _normalize_text(document.get("volunteer_id")),
        "volunteer_name": _normalize_text(document.get("volunteer_name")) or "Volunteer",
        "task_status": task_status,
        "event_type": event_type,
        "message": _normalize_text(document.get("message")),
        "source_notification_id": _normalize_text(document.get("source_notification_id")) or None,
        "triggered_by_user_id": _normalize_text(document.get("triggered_by_user_id")) or None,
        "created_at": created_at.isoformat() if created_at else "",
    }


async def _get_staff_user_ids_for_ngo(ngo_id: str) -> List[str]:
    staff_user_ids: List[str] = []

    users_query = {
        "$or": [
            {"ngo_id": ngo_id},
            {"ngoId": ngo_id},
            {"organization_id": ngo_id},
            {"organizationId": ngo_id},
        ]
    }
    user_documents = await users_collection.find(users_query).limit(2000).to_list(length=2000)

    for user_document in user_documents:
        role = _extract_role(user_document)
        if not _is_staff_role(role):
            continue

        user_id = _extract_user_id(user_document)
        if user_id:
            staff_user_ids.append(user_id)

    memberships_query = {
        "$and": [
            {
                "$or": [
                    {"ngo_id": ngo_id},
                    {"ngoId": ngo_id},
                    {"organization_id": ngo_id},
                    {"organizationId": ngo_id},
                ]
            },
            {"status": {"$nin": ["inactive", "removed"]}},
            {"is_active": {"$ne": False}},
        ]
    }

    membership_documents = await membership_collection.find(memberships_query).limit(2000).to_list(
        length=2000
    )

    for membership_document in membership_documents:
        if not _is_active_membership(membership_document):
            continue

        role = _extract_role(membership_document)
        if not _is_staff_role(role):
            continue

        user_id = _extract_user_id(membership_document)
        if user_id:
            staff_user_ids.append(user_id)

    return list(dict.fromkeys(staff_user_ids))


async def _is_staff_user_for_ngo(user_id: str, ngo_id: str) -> bool:
    staff_user_ids = await _get_staff_user_ids_for_ngo(ngo_id)
    return _normalize_text(user_id) in set(staff_user_ids)


def _build_staff_message(
    need_type: str,
    volunteer_name: str,
    task_status: str,
    event_type: str,
) -> str:
    if event_type == "assigned":
        return (
            f"Task for need '{need_type}' assigned to volunteer '{volunteer_name}'. "
            f"Current status is {task_status}."
        )

    return (
        f"Volunteer '{volunteer_name}' updated task status for need '{need_type}' to {task_status}."
    )


async def _create_staff_notifications_for_event(
    *,
    ngo_id: str,
    need_id: str,
    need_type: str,
    urgency: str,
    volunteer_id: str,
    volunteer_name: str,
    task_status: str,
    event_type: str,
    source_notification_id: Optional[str] = None,
    triggered_by_user_id: Optional[str] = None,
) -> Dict[str, int]:
    staff_user_ids = await _get_staff_user_ids_for_ngo(ngo_id)
    if not staff_user_ids:
        return {"created": 0, "skipped": 0}

    created_count = 0
    skipped_count = 0
    now = datetime.now(timezone.utc)

    normalized_status = _normalize_text(task_status).lower()
    if normalized_status not in _ALLOWED_TASK_STATUS:
        normalized_status = "pending"

    normalized_event_type = _normalize_text(event_type).lower()
    if normalized_event_type not in _ALLOWED_EVENT_TYPES:
        normalized_event_type = "assigned"

    message = _build_staff_message(
        need_type=need_type,
        volunteer_name=volunteer_name,
        task_status=normalized_status,
        event_type=normalized_event_type,
    )

    for staff_user_id in staff_user_ids:
        notification_document = {
            "ngo_id": ngo_id,
            "recipient_user_id": staff_user_id,
            "need_id": need_id,
            "need_type": need_type,
            "urgency": urgency,
            "volunteer_id": volunteer_id,
            "volunteer_name": volunteer_name,
            "task_status": normalized_status,
            "event_type": normalized_event_type,
            "message": message,
            "source_notification_id": _normalize_text(source_notification_id) or None,
            "triggered_by_user_id": _normalize_text(triggered_by_user_id) or None,
            "created_at": now,
        }

        try:
            await staff_notifications_collection.insert_one(notification_document)
            created_count += 1
        except Exception:
            skipped_count += 1
            continue

        websocket_payload = json.dumps(
            {
                "type": "staff_task_notification",
                "need_id": need_id,
                "need_type": need_type,
                "volunteer_id": volunteer_id,
                "volunteer_name": volunteer_name,
                "task_status": normalized_status,
                "event_type": normalized_event_type,
                "recipient_user_id": staff_user_id,
                "message": message,
            },
            ensure_ascii=True,
        )

        try:
            await manager.send_personal_message(staff_user_id, websocket_payload)
        except Exception:
            pass

    return {
        "created": created_count,
        "skipped": skipped_count,
    }


async def create_staff_notifications_for_ranked_volunteers(
    ranked_result: Dict[str, Any],
    ngo_id: str,
) -> Dict[str, int]:
    if not isinstance(ranked_result, dict):
        return {"created": 0, "skipped": 0}

    need = ranked_result.get("need")
    ranked_volunteers = ranked_result.get("ranked_volunteers")
    if not isinstance(need, dict) or not isinstance(ranked_volunteers, list):
        return {"created": 0, "skipped": 0}

    need_id = _normalize_text(need.get("need_id"))
    need_type = _normalize_text(need.get("need_type")) or "Unknown"
    urgency = _normalize_urgency(need.get("urgency"))

    created_total = 0
    skipped_total = 0

    for volunteer in ranked_volunteers:
        if not isinstance(volunteer, dict):
            skipped_total += 1
            continue

        volunteer_id = _normalize_text(volunteer.get("volunteer_id"))
        if not volunteer_id:
            skipped_total += 1
            continue

        volunteer_name = _normalize_text(volunteer.get("volunteer_name")) or "Volunteer"

        result = await _create_staff_notifications_for_event(
            ngo_id=ngo_id,
            need_id=need_id,
            need_type=need_type,
            urgency=urgency,
            volunteer_id=volunteer_id,
            volunteer_name=volunteer_name,
            task_status="pending",
            event_type="assigned",
        )
        created_total += int(result.get("created", 0))
        skipped_total += int(result.get("skipped", 0))

    return {
        "created": created_total,
        "skipped": skipped_total,
    }


async def create_staff_notifications_for_task_status_change(
    notification_document: Dict[str, Any],
    task_status: str,
    ngo_id: str,
    triggered_by_user_id: Optional[str] = None,
) -> Dict[str, int]:
    need_id = _normalize_text(notification_document.get("need_id"))
    need_type = _normalize_text(notification_document.get("need_type")) or "Unknown"
    urgency = _normalize_urgency(notification_document.get("urgency"))
    volunteer_id = _normalize_text(notification_document.get("volunteer_id"))
    volunteer_name = _normalize_text(notification_document.get("volunteer_name")) or "Volunteer"
    source_notification_id = _normalize_text(notification_document.get("_id"))

    return await _create_staff_notifications_for_event(
        ngo_id=ngo_id,
        need_id=need_id,
        need_type=need_type,
        urgency=urgency,
        volunteer_id=volunteer_id,
        volunteer_name=volunteer_name,
        task_status=task_status,
        event_type="status_changed",
        source_notification_id=source_notification_id,
        triggered_by_user_id=triggered_by_user_id,
    )


async def get_staff_notifications_for_user(data, user_id: str, ngo_id: str) -> Dict[str, Any]:
    if not await _is_staff_user_for_ngo(user_id, ngo_id):
        raise HTTPException(status_code=403, detail="Only staff users can view staff notifications")

    query: Dict[str, Any] = {
        "ngo_id": ngo_id,
        "recipient_user_id": user_id,
    }

    if data.task_status:
        query["task_status"] = data.task_status

    if data.event_type:
        query["event_type"] = data.event_type

    documents = (
        await staff_notifications_collection.find(query)
        .sort("created_at", -1)
        .limit(data.limit)
        .to_list(length=data.limit)
    )

    items = [_serialize_staff_notification(document) for document in documents]
    return {
        "total": len(items),
        "items": items,
    }
