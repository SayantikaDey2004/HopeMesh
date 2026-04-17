from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.DB_NAME]
users_collection = db['users']
ngo_collection = db['ngos']
membership_collection = db['memberships']