from typing import List, Literal, Optional

from pydantic import BaseModel


class StaffNotificationItemSchema(BaseModel):
    staff_notification_id: str
    ngo_id: str
    recipient_user_id: str
    need_id: str
    need_type: str
    urgency: Literal["Low", "Medium", "High", "Critical", "Unknown"]
    volunteer_id: str
    volunteer_name: str
    task_status: Literal["pending", "accepted", "rejected"]
    event_type: Literal["assigned", "status_changed"]
    message: str
    source_notification_id: Optional[str] = None
    triggered_by_user_id: Optional[str] = None
    created_at: str


class StaffNotificationListResponseSchema(BaseModel):
    total: int
    items: List[StaffNotificationItemSchema]
