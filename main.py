from fastapi import FastAPI
from app.db.db import client
from app.routers.authRouter import router as auth_router

app = FastAPI()
app.include_router(auth_router)


@app.on_event("startup")
async def startup_db_ping():
    await client.admin.command("ping")


@app.get("/")
def root():
    return {"message": "API is working!"}