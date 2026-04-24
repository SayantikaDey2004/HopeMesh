from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.Validation.notificationValidation import (
    VolunteerNotificationListValidationSchema,
    VolunteerNotificationStatusUpdateValidationSchema,
)
from app.core.dependencies import get_current_ngo_id, get_current_token_payload
from app.core.websocketConfig import manager
from app.models.notificationSchema import (
    VolunteerNotificationListResponseSchema,
    VolunteerNotificationStatusUpdateResponseSchema,
)
from app.services.notification.Notification import (
    get_volunteer_notifications,
    update_notification_task_status,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me", response_model=VolunteerNotificationListResponseSchema)
async def get_my_notifications_controller(
    task_status: Optional[Literal["pending", "accepted", "rejected"]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    payload: dict = Depends(get_current_token_payload),
    ngo_id: str = Depends(get_current_ngo_id),
):
    data = VolunteerNotificationListValidationSchema(
        task_status=task_status,
        limit=limit,
    )

    return await get_volunteer_notifications(data, payload["user_id"], ngo_id)


@router.patch(
    "/{notification_id}/status",
    response_model=VolunteerNotificationStatusUpdateResponseSchema,
)
async def update_notification_status_controller(
    notification_id: str,
    data: VolunteerNotificationStatusUpdateValidationSchema,
    payload: dict = Depends(get_current_token_payload),
    ngo_id: str = Depends(get_current_ngo_id),
):
    return await update_notification_task_status(
        notification_id=notification_id,
        data=data,
        user_id=payload["user_id"],
        ngo_id=ngo_id,
    )


@router.websocket("/ws/{user_id}")
async def notifications_websocket(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception:
        manager.disconnect(user_id)
