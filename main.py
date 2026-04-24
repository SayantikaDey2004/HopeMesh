import asyncio

from fastapi import FastAPI, HTTPException
from app.db.db import client
from app.routers.authRouter import router as auth_router
from app.routers.dashboardRouter import router as dashboard_router
from app.routers.historyRouter import router as history_router
from app.routers.notificationRouter import router as notification_router
from app.routers.surveyDataControlRouter import router as survey_data_control_router
from app.routers.volunteerMatchingRouter import router as volunteer_matching_router
from app.api.v1.routes.email import router as email_router
from app.core.config import get_settings
from app.services.email.sendEmail import send_email
from app.services.notification.Notification import run_pending_notification_rematch_worker

settings = get_settings()
app = FastAPI(title=settings.APP_NAME)
notification_rematch_worker_task = None
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(history_router)
app.include_router(notification_router)
app.include_router(survey_data_control_router)
app.include_router(volunteer_matching_router)
app.include_router(email_router)


@app.on_event("startup")
async def startup_db_ping():
    global notification_rematch_worker_task

    await client.admin.command("ping")
    notification_rematch_worker_task = asyncio.create_task(
        run_pending_notification_rematch_worker()
    )


@app.on_event("shutdown")
async def shutdown_background_tasks():
    global notification_rematch_worker_task

    if notification_rematch_worker_task is None:
        return

    notification_rematch_worker_task.cancel()
    try:
        await notification_rematch_worker_task
    except asyncio.CancelledError:
        pass


@app.get("/")
def root():
    return {"message": "API is working!"}


@app.post("/send-test-email")
def send_test_email():
    try:
        send_email(
            to_email="student@example.com",
            to_name="Student",
            subject="Welcome",
            html_content="<h1>Hello from Brevo</h1>",
        )
        return {"ok": True}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))