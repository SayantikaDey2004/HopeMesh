from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from Validation.staffNotificationValidation import StaffNotificationListValidationSchema
from core.dependencies import get_current_ngo_id, get_current_token_payload
from core.websocketConfig import manager
from models.staffNotificationSchema import StaffNotificationListResponseSchema
from services.staffNotification.StaffNotification import get_staff_notifications_for_user

router = APIRouter(prefix="/staff-notifications", tags=["Staff Notifications"])


@router.get("/me", response_model=StaffNotificationListResponseSchema)
async def get_my_staff_notifications_controller(
    task_status: Optional[Literal["pending", "accepted", "rejected"]] = Query(default=None),
    event_type: Optional[Literal["assigned", "status_changed"]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    payload: dict = Depends(get_current_token_payload),
    ngo_id: str = Depends(get_current_ngo_id),
):
    data = StaffNotificationListValidationSchema(
        task_status=task_status,
        event_type=event_type,
        limit=limit,
    )

    return await get_staff_notifications_for_user(data, payload["user_id"], ngo_id)


@router.websocket("/ws/{user_id}")
async def staff_notifications_websocket(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception:
        manager.disconnect(user_id)
