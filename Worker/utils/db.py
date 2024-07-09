import os
from typing import List, Any
import motor.motor_asyncio
from pydantic import BaseModel
import redis


client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{os.getenv("MONGO_USERNAME")}:{os.getenv("MONGO_PASSWORD")}@{os.getenv("MONGO_HOST")}:{os.getenv("MONGO_PORT")}')
db = client[os.getenv("MONGO_DB_NAME")]
rdb = redis.Redis(host=os.getenv('REDIS_HOST'), port=int(os.getenv('REDIS_PORT')), password=os.getenv('REDIS_PASSWORD'))