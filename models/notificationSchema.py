from typing import List, Literal, Optional

from pydantic import BaseModel


class VolunteerNotificationItemSchema(BaseModel):
    notification_id: str
    ngo_id: str
    need_id: str
    need_location: str
    volunteer_id: str
    recipient_user_id: str
    volunteer_name: str
    need_type: str
    urgency: Literal["Low", "Medium", "High", "Critical", "Unknown"]
    message: str
    task_status: Literal["pending", "accepted", "rejected"]
    created_at: str
    updated_at: str
    responded_at: Optional[str] = None


class VolunteerNotificationListResponseSchema(BaseModel):
    total: int
    items: List[VolunteerNotificationItemSchema]


class VolunteerNotificationStatusUpdateResponseSchema(BaseModel):
    message: str
    notification: VolunteerNotificationItemSchema
