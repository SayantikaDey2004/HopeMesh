from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.DB_NAME]
users_collection = db['users']
ngo_collection = db['ngos']
membership_collection = db['memberships']
password_reset_tokens_collection = db['password_reset_tokens']
needs_collection = db['needs']
volunteers_collection = db['volunteers']
survey_data_control_collection = db['survey_data_control']
notifications_collection = db['notifications']
staff_notifications_collection = db['staff_notifications']