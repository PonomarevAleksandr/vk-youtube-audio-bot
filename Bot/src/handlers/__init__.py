__all__ = ("router",)

from aiogram import Router

router = Router()
from .user import router as user_router

router.include_routers(user_router)
