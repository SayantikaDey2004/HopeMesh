from fastapi import APIRouter, HTTPException

from schemas.email import EmailRequest
from services.brevo_email import send_email

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/send")
def send_email_route(payload: EmailRequest):
    try:
        send_email(
            to_email=payload.to_email,
            to_name=payload.to_name,
            subject=payload.subject,
            html_content=payload.html_content,
        )
        return {"ok": True, "message": "Email sent"}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
