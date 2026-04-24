import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.core.websocketConfig import manager
from app.db.db import (
    notifications_collection,
    survey_data_control_collection,
    users_collection,
    volunteers_collection,
)

_ALLOWED_URGENCY = {"Low", "Medium", "High", "Critical", "Unknown"}
_ALLOWED_TASK_STATUS = {"pending", "accepted", "rejected"}
_VOLUNTEER_ROLES = {"volunteer", "volunteers"}
_PENDING_RESPONSE_TIMEOUT_HOURS = 2
_PENDING_RECHECK_INTERVAL_SECONDS = 300
_PENDING_TIMEOUT_BATCH_SIZE = 100


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
        or document.get("type")
    ).lower()
    return role


def _has_volunteer_role(document: Dict[str, Any]) -> bool:
    role = _extract_role(document)
    if not role:
        return True

    return role in _VOLUNTEER_ROLES


def _build_identifier_filters(value: str) -> list[Dict[str, Any]]:
    filters: list[Dict[str, Any]] = [{"_id": value}]
    if ObjectId.is_valid(value):
        filters.insert(0, {"_id": ObjectId(value)})

    return filters


async def _find_volunteer_document(volunteer_id: str) -> Optional[Dict[str, Any]]:
    normalized_id = _normalize_text(volunteer_id)
    if not normalized_id:
        return None

    id_filters = _build_identifier_filters(normalized_id)
    return await volunteers_collection.find_one(
        {
            "$or": id_filters
            + [
                {"volunteer_id": normalized_id},
                {"user_id": normalized_id},
                {"userId": normalized_id},
            ]
        }
    )


async def _find_user_document(user_id: str) -> Optional[Dict[str, Any]]:
    normalized_id = _normalize_text(user_id)
    if not normalized_id:
        return None

    id_filters = _build_identifier_filters(normalized_id)
    return await users_collection.find_one(
        {
            "$or": id_filters
            + [
                {"user_id": normalized_id},
                {"userId": normalized_id},
            ]
        }
    )


async def _resolve_recipient_user_id(volunteer_id: str) -> tuple[str, Optional[Dict[str, Any]]]:
    volunteer_document = await _find_volunteer_document(volunteer_id)
    if volunteer_document:
        recipient_user_id = _normalize_text(
            volunteer_document.get("user_id")
            or volunteer_document.get("userId")
            or volunteer_document.get("_id")
            or volunteer_document.get("volunteer_id")
        )
        if recipient_user_id:
            return recipient_user_id, volunteer_document

    return _normalize_text(volunteer_id), volunteer_document


def _build_notification_message(need: Dict[str, Any], volunteer_name: str) -> str:
    need_type = _normalize_text(need.get("need_type") or "General Need")
    urgency = _normalize_urgency(need.get("urgency"))
    safe_name = _normalize_text(volunteer_name) or "Volunteer"
    return (
        f"Hi {safe_name}, you have a new matched task ({need_type}) with {urgency} urgency. "
        "Please accept or reject this task."
    )


def _serialize_notification(document: Dict[str, Any]) -> Dict[str, Any]:
    created_at = document.get("created_at")
    updated_at = document.get("updated_at")
    responded_at = document.get("responded_at")

    task_status = _normalize_text(document.get("task_status")).lower()
    if task_status not in _ALLOWED_TASK_STATUS:
        task_status = "pending"

    return {
        "notification_id": _normalize_text(document.get("_id") or document.get("notification_id")),
        "ngo_id": _normalize_text(document.get("ngo_id")),
        "need_id": _normalize_text(document.get("need_id")),
        "volunteer_id": _normalize_text(document.get("volunteer_id")),
        "recipient_user_id": _normalize_text(document.get("recipient_user_id")),
        "volunteer_name": _normalize_text(document.get("volunteer_name")) or "Volunteer",
        "need_type": _normalize_text(document.get("need_type")) or "Unknown",
        "urgency": _normalize_urgency(document.get("urgency")),
        "message": _normalize_text(document.get("message")),
        "task_status": task_status,
        "created_at": created_at.isoformat() if created_at else "",
        "updated_at": updated_at.isoformat() if updated_at else "",
        "responded_at": responded_at.isoformat() if responded_at else None,
    }


async def create_notifications_for_ranked_volunteers(
    ranked_result: Dict[str, Any], ngo_id: str
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

    created_count = 0
    skipped_count = 0

    for volunteer in ranked_volunteers:
        if not isinstance(volunteer, dict):
            skipped_count += 1
            continue

        volunteer_id = _normalize_text(volunteer.get("volunteer_id"))
        if not volunteer_id:
            skipped_count += 1
            continue

        recipient_user_id, volunteer_document = await _resolve_recipient_user_id(volunteer_id)
        if not recipient_user_id:
            skipped_count += 1
            continue

        if volunteer_document and not _has_volunteer_role(volunteer_document):
            skipped_count += 1
            continue

        user_document = await _find_user_document(recipient_user_id)
        if user_document and not _has_volunteer_role(user_document):
            skipped_count += 1
            continue

        now = datetime.now(timezone.utc)
        volunteer_name = _normalize_text(volunteer.get("volunteer_name")) or "Volunteer"
        message = _build_notification_message(need, volunteer_name)

        notification_document = {
            "ngo_id": ngo_id,
            "need_id": need_id,
            "volunteer_id": volunteer_id,
            "recipient_user_id": recipient_user_id,
            "volunteer_name": volunteer_name,
            "need_type": need_type,
            "urgency": urgency,
            "message": message,
            "task_status": "pending",
            "created_at": now,
            "updated_at": now,
            "responded_at": None,
        }

        upsert_result = await notifications_collection.update_one(
            {
                "$and": [
                    {"ngo_id": ngo_id},
                    {"need_id": need_id},
                    {"recipient_user_id": recipient_user_id},
                    {"task_status": "pending"},
                ]
            },
            {"$setOnInsert": notification_document},
            upsert=True,
        )

        if upsert_result.upserted_id is None:
            skipped_count += 1
            continue

        created_count += 1

        websocket_payload = json.dumps(
            {
                "type": "task_notification",
                "need_id": need_id,
                "task_status": "pending",
                "message": message,
                "recipient_user_id": recipient_user_id,
            },
            ensure_ascii=True,
        )
        try:
            await manager.send_personal_message(recipient_user_id, websocket_payload)
        except Exception:
            pass

    return {
        "created": created_count,
        "skipped": skipped_count,
    }


async def get_volunteer_notifications(data, user_id: str, ngo_id: str) -> Dict[str, Any]:
    query: Dict[str, Any] = {
        "ngo_id": ngo_id,
        "recipient_user_id": user_id,
    }

    if data.task_status:
        query["task_status"] = data.task_status

    documents = (
        await notifications_collection.find(query)
        .sort("created_at", -1)
        .limit(data.limit)
        .to_list(length=data.limit)
    )

    items = [_serialize_notification(document) for document in documents]
    return {
        "total": len(items),
        "items": items,
    }


async def _fetch_need_document_by_need_id(need_id: str, ngo_id: str) -> Optional[Dict[str, Any]]:
    normalized_need_id = _normalize_text(need_id)
    if not normalized_need_id:
        return None

    query_or: List[Dict[str, Any]] = [
        {"need_id": normalized_need_id},
        {"_id": normalized_need_id},
    ]
    if ObjectId.is_valid(normalized_need_id):
        query_or.insert(0, {"_id": ObjectId(normalized_need_id)})

    return await survey_data_control_collection.find_one(
        {
            "$and": [
                {"ngo_id": ngo_id},
                {"$or": query_or},
            ]
        }
    )


async def _collect_excluded_volunteer_ids(need_id: str, ngo_id: str) -> List[str]:
    distinct_ids = await notifications_collection.distinct(
        "volunteer_id",
        {
            "ngo_id": ngo_id,
            "need_id": need_id,
        },
    )
    return list(
        dict.fromkeys(
            [
                _normalize_text(volunteer_id)
                for volunteer_id in distinct_ids
                if _normalize_text(volunteer_id)
            ]
        )
    )


async def _mark_rematch_triggered(
    notification_document: Dict[str, Any],
    reason: str,
    replacement_created: bool,
) -> None:
    notification_internal_id = notification_document.get("_id")
    if notification_internal_id is None:
        return

    now = datetime.now(timezone.utc)
    await notifications_collection.update_one(
        {"_id": notification_internal_id},
        {
            "$set": {
                "rematch_triggered_at": now,
                "rematch_reason": reason,
                "replacement_created": replacement_created,
                "updated_at": now,
            }
        },
    )


async def _trigger_replacement_match(
    notification_document: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    need_id = _normalize_text(notification_document.get("need_id"))
    ngo_id = _normalize_text(notification_document.get("ngo_id"))

    if not need_id or not ngo_id:
        await _mark_rematch_triggered(notification_document, reason, False)
        return {
            "replacement_created": False,
            "created": 0,
            "skipped": 0,
        }

    need_document = await _fetch_need_document_by_need_id(need_id, ngo_id)
    processing_status = _normalize_text((need_document or {}).get("processing_status")).lower()
    if not need_document or processing_status != "processed":
        await _mark_rematch_triggered(notification_document, reason, False)
        return {
            "replacement_created": False,
            "created": 0,
            "skipped": 0,
        }

    excluded_volunteer_ids = await _collect_excluded_volunteer_ids(need_id, ngo_id)
    current_volunteer_id = _normalize_text(notification_document.get("volunteer_id"))
    if current_volunteer_id and current_volunteer_id not in excluded_volunteer_ids:
        excluded_volunteer_ids.append(current_volunteer_id)

    from app.services.matching.VolunteerMatching import rank_volunteers_for_document

    ranked_result = await rank_volunteers_for_document(
        need_document=need_document,
        ngo_id=ngo_id,
        max_volunteers=100,
        max_ranked_results=1,
        excluded_volunteer_ids=excluded_volunteer_ids,
    )

    creation_result = await create_notifications_for_ranked_volunteers(ranked_result, ngo_id)
    replacement_created = creation_result.get("created", 0) > 0

    await _mark_rematch_triggered(notification_document, reason, replacement_created)
    return {
        "replacement_created": replacement_created,
        "created": int(creation_result.get("created", 0)),
        "skipped": int(creation_result.get("skipped", 0)),
    }


async def update_notification_task_status(
    notification_id: str,
    data,
    user_id: str,
    ngo_id: str,
) -> Dict[str, Any]:
    normalized_notification_id = _normalize_text(notification_id)
    if not normalized_notification_id:
        raise HTTPException(status_code=400, detail="Invalid notification_id")

    notification_lookup_filters = [
        {"_id": normalized_notification_id},
        {"notification_id": normalized_notification_id},
    ]
    if ObjectId.is_valid(normalized_notification_id):
        notification_lookup_filters.insert(0, {"_id": ObjectId(normalized_notification_id)})

    scoped_query = {
        "$and": [
            {"$or": notification_lookup_filters},
            {"ngo_id": ngo_id},
            {"recipient_user_id": user_id},
        ]
    }

    now = datetime.now(timezone.utc)
    update_fields: Dict[str, Any] = {
        "task_status": data.task_status,
        "updated_at": now,
    }

    if data.task_status in {"accepted", "rejected"}:
        update_fields["responded_at"] = now
    else:
        update_fields["responded_at"] = None

    update_result = await notifications_collection.update_one(
        scoped_query,
        {"$set": update_fields},
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")

    document = await notifications_collection.find_one(scoped_query)
    if not document:
        raise HTTPException(status_code=404, detail="Notification not found")

    replacement_created = False
    if data.task_status == "rejected":
        rematch_result = await _trigger_replacement_match(
            document,
            reason="rejected_by_volunteer",
        )
        replacement_created = bool(rematch_result.get("replacement_created"))

        refreshed_document = await notifications_collection.find_one(scoped_query)
        if refreshed_document:
            document = refreshed_document

    serialized_notification = _serialize_notification(document)

    websocket_payload = json.dumps(
        {
            "type": "task_status_updated",
            "notification_id": serialized_notification["notification_id"],
            "task_status": serialized_notification["task_status"],
            "need_id": serialized_notification["need_id"],
        },
        ensure_ascii=True,
    )
    try:
        await manager.send_personal_message(user_id, websocket_payload)
    except Exception:
        pass

    message = "Notification task status updated successfully"
    if data.task_status == "rejected":
        if replacement_created:
            message = "Task rejected. Replacement volunteer matched automatically"
        else:
            message = "Task rejected. No replacement volunteer found"

    return {
        "message": message,
        "notification": serialized_notification,
    }


async def process_pending_notification_timeouts(
    batch_size: int = _PENDING_TIMEOUT_BATCH_SIZE,
) -> Dict[str, int]:
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=_PENDING_RESPONSE_TIMEOUT_HOURS)

    stale_notifications = (
        await notifications_collection.find(
            {
                "$and": [
                    {"task_status": "pending"},
                    {"created_at": {"$lte": cutoff_time}},
                    {"rematch_triggered_at": {"$exists": False}},
                ]
            }
        )
        .sort("created_at", 1)
        .limit(batch_size)
        .to_list(length=batch_size)
    )

    processed_count = 0
    replacement_count = 0

    for notification_document in stale_notifications:
        notification_internal_id = notification_document.get("_id")
        if notification_internal_id is None:
            continue

        now = datetime.now(timezone.utc)
        claim_result = await notifications_collection.update_one(
            {
                "$and": [
                    {"_id": notification_internal_id},
                    {"task_status": "pending"},
                    {"rematch_triggered_at": {"$exists": False}},
                ]
            },
            {
                "$set": {
                    "task_status": "rejected",
                    "updated_at": now,
                    "responded_at": now,
                    "auto_rejected_due_to_timeout": True,
                    "timeout_hours": _PENDING_RESPONSE_TIMEOUT_HOURS,
                }
            },
        )

        if claim_result.matched_count == 0:
            continue

        processed_count += 1

        claimed_document = await notifications_collection.find_one({"_id": notification_internal_id})
        if not claimed_document:
            continue

        rematch_result = await _trigger_replacement_match(
            claimed_document,
            reason="no_response_timeout",
        )
        if rematch_result.get("replacement_created"):
            replacement_count += 1

    return {
        "timed_out_processed": processed_count,
        "replacements_created": replacement_count,
    }


async def run_pending_notification_rematch_worker():
    while True:
        try:
            await process_pending_notification_timeouts()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

        await asyncio.sleep(_PENDING_RECHECK_INTERVAL_SECONDS)
