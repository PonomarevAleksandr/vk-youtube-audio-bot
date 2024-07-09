from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update
from motor.motor_asyncio import AsyncIOMotorClient
from redis.client import Redis


class DataBaseMiddleware(BaseMiddleware):
    def __init__(self, db: AsyncIOMotorClient, rdb: Redis):
        super().__init__()
        self.db = db
        self.rdb = rdb

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        data["rdb"] = self.rdb
        data["db"] = self.db
        return await handler(event, data)
