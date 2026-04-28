import asyncio

from services.email.generateResetPasswordEmailHTML import (
    generate_reset_password_email_html,
)
from services.email.sendEmail import send_email


async def send_reset_password_email(to_email: str, reset_link: str) -> None:
    html_content = generate_reset_password_email_html(reset_link)

    def _send() -> None:
        send_email(
            to_email=to_email,
            to_name="User",
            subject="Reset your password",
            html_content=html_content,
        )

    try:
        await asyncio.to_thread(_send)
    except Exception as error:
        raise RuntimeError(f"Brevo request failed: {error}") from error
