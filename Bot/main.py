import os
import logging

import asyncio
import redis
from aiogram import Dispatcher, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage
from fluent_compiler.bundle import FluentBundle
from fluentogram import FluentTranslator
from fluentogram import TranslatorHub

from config import load_env
from src.utils.db import db

from src.handlers import router as main_router
from src.middlewares.db_middleware import DataBaseMiddleware
from src.middlewares.throttling_middleware import ThrottlingMiddleware
from src.middlewares.translate_middleware import TranslateMiddleware
from src.middlewares.user_middleware import UserMiddleware

logging.basicConfig(level=logging.INFO)
load_env()

t_hub = TranslatorHub(
    {
        "kk": ('kk', 'en', 'kz'),
        "uz": ('uz', 'en'),
        "uk": ('uk', 'en', 'ua'),
        "ru": ("ru", "en", "ar"),
        "en": ("en", "ar")
    },
    translators=[
        FluentTranslator(
            "ru",
            translator=FluentBundle.from_files(
                "ru-RU",
                filenames=[
                    "/bot/src/i18n/user/ru/text.ftl",
                    "/bot/src/i18n/user/ru/button.ftl"
                ], )),
        FluentTranslator(
            "en",
            translator=FluentBundle.from_files(
                "en-US",
                filenames=[
                    "/bot/src/i18n/user/en/text.ftl",
                    "/bot/src/i18n/user/en/button.ftl"
                ]
            )
        ),
        FluentTranslator(
            "uz",
            translator=FluentBundle.from_files(
                "uz-UZ",
                filenames=[
                    "/bot/src/i18n/user/uz/text.ftl",
                    "/bot/src/i18n/user/uz/button.ftl"
                ]
            )
        ),
        FluentTranslator(
            "uk",
            translator=FluentBundle.from_files(
                "uk-UA",
                filenames=[
                    "/bot/src/i18n/user/uk/text.ftl",
                    "/bot/src/i18n/user/uk/button.ftl"
                ]
            )
        ),
        FluentTranslator(
            "kk",
            translator=FluentBundle.from_files(
                "kk-KZ",
                filenames=[
                    "/bot/src/i18n/user/kk/text.ftl",
                    "/bot/src/i18n/user/kk/button.ftl"
                ]
            )
        ),

    ],
    root_locale="ru"
)


async def main():
    session = AiohttpSession()
    bot_settings = {"session": session, "parse_mode": "HTML"}
    bot = Bot(token=os.getenv("BOT_TOKEN"), **bot_settings)
    storage = RedisStorage.from_url(
        url=f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/0")
    rdb = redis.Redis(host=os.getenv('REDIS_HOST'), port=int(os.getenv('REDIS_PORT')),
                      password=os.getenv('REDIS_PASSWORD'))
    dp = Dispatcher(storage=storage, t_hub=t_hub)

    dp.message.middleware(ThrottlingMiddleware())
    dp.message.outer_middleware(DataBaseMiddleware(db=db, rdb=rdb))
    dp.message.outer_middleware(UserMiddleware())
    dp.message.outer_middleware(TranslateMiddleware())
    # ---
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.callback_query.outer_middleware(DataBaseMiddleware(db=db, rdb=rdb))
    dp.callback_query.outer_middleware(UserMiddleware())
    dp.callback_query.outer_middleware(TranslateMiddleware())

    dp.include_router(main_router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
