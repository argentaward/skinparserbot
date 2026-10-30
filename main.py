import asyncio
import logging
import sys
from urllib.parse import urlsplit

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

def _mask_proxy(url: str) -> str:
    try:
        parts = urlsplit(url)
        if parts.username and parts.password:
            return url.replace(f":{parts.password}@", ":***@")
        return url
    except Exception:
        return "configured"

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
        # Автоматическая коррекция формата socks5://user:pass:ip:port -> socks5://user:pass@ip:port если пользователь опечатался
        proxy_url = settings.PROXY_URL.strip()
        parts = proxy_url.split(":")
        if len(parts) == 5 and "@" not in proxy_url:
            # format scheme://user:pass:ip:port
            scheme_and_user = f"{parts[0]}:{parts[1]}"
            proxy_url = f"{scheme_and_user}:{parts[2]}@{parts[3]}:{parts[4]}"

        logger.info(f"Используется прокси для Telegram API: {_mask_proxy(proxy_url)}")
        session = AiohttpSession(proxy=proxy_url)

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
