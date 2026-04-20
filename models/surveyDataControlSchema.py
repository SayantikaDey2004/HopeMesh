from typing import List, Literal, Optional

from pydantic import BaseModel


class SurveyDataControlCreateResponseSchema(BaseModel):
    message: str
    survey_id: str


class SurveyDataControlItemSchema(BaseModel):
    survey_id: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    location: str
    city_area: str
    pin_code: str
    submitted_by: Literal["NGO", "Volunteer", "Citizen"]
    need_type: Literal[
        "Food shortage",
        "Medical help",
        "Shelter",
        "Education",
        "Disaster relief",
        "Other",
    ]
    other_need_text: Optional[str] = None
    description: str
    urgency_level: Literal["Low", "Medium", "High", "Critical"]
    people_affected: Literal["1-10", "10-50", "50-100", "100+"]
    required_resources: List[
        Literal[
            "Food",
            "Water",
            "Medicines",
            "Doctors",
            "Volunteers",
            "Transport",
            "Shelter",
        ]
    ]
    time_sensitivity: Literal[
        "Immediate (within 24 hrs)",
        "Within 2-3 days",
        "Within a week",
    ]
    contact_preference: Literal["Phone", "Email"]
    created_at: str


class SurveyDataControlListResponseSchema(BaseModel):
    total: int
    items: List[SurveyDataControlItemSchema]