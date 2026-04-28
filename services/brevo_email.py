import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from core.config import get_settings
from services.email.emailConfig import email_api

settings = get_settings()


def send_email(to_email: str, to_name: str, subject: str, html_content: str):
    api_key = settings.brevo_api_key or settings.BREVO_API_KEY
    if not api_key:
        raise RuntimeError("Missing Brevo API key in environment")

    sender_email = settings.EMAIL_FROM or settings.BREVO_SENDER_EMAIL
    if not sender_email:
        raise RuntimeError("Missing EMAIL_FROM or BREVO_SENDER_EMAIL in environment")

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender={"email": sender_email, "name": settings.APP_NAME},
        to=[{"email": to_email, "name": to_name}],
        subject=subject,
        html_content=html_content,
    )

    try:
        email_api.send_transac_email(send_smtp_email)
    except ApiException as error:
        raise RuntimeError(f"Brevo API error: {error}") from error
