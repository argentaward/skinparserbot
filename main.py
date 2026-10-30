import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import settings
from bot.database.db import init_db
from bot.handlers import common, search, compare, profile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("skinparserbot")

async def main():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных готова.")

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or settings.BOT_TOKEN == "DUMMY_TOKEN":
        logger.warning(
            "⚠️ ВНИМАНИЕ: BOT_TOKEN не задан или содержит заглушку! "
            "Пожалуйста, создайте файл .env и укажите ваш BOT_TOKEN=..."
        )

    session = None
    if settings.PROXY_URL:
        logger.info(f"Используется прокси для Telegram API: {settings.PROXY_URL}")
        session = AiohttpSession(proxy=settings.PROXY_URL)

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(common.router)
    dp.include_router(search.router)
    dp.include_router(compare.router)
    dp.include_router(profile.router)

    logger.info("Запуск бота в режиме Polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
