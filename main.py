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
from bot.database.db import init_db, get_total_prices_count
from bot.handlers import common, search, compare, profile
from bot.services.market_service import update_all_market_prices

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

def _sanitize_token(raw_token: str) -> str:
    if not raw_token:
        return ""
    token = raw_token.strip().strip("'\"")
    if token.startswith("BOT_TOKEN="):
        token = token[len("BOT_TOKEN="):].strip().strip("'\"")
    return token

async def background_prices_updater():
    """
    Фоновый цикл обновления котировок маркетов (Market.CSGO и Skinport) каждые 10 минут
    """
    while True:
        try:
            logger.info("Фоновое обновление котировок всех маркетов...")
            await update_all_market_prices()
        except Exception as e:
            logger.error(f"Ошибка при фоновом обновлении котировок: {e}")
        await asyncio.sleep(600)

async def main():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных готова.")

    cstm_count = await get_total_prices_count("Market.CSGO")
    skinport_count = await get_total_prices_count("Skinport")
    logger.info(f"В локальной базе котировок: Market.CSGO={cstm_count}, Skinport={skinport_count}")

    token = _sanitize_token(settings.BOT_TOKEN)

    if not token or token in ("YOUR_BOT_TOKEN_HERE", "DUMMY_TOKEN"):
        logger.warning(
            "⚠️ ВНИМАНИЕ: BOT_TOKEN не задан или содержит заглушку! "
            "Пожалуйста, укажите валидный BOT_TOKEN в переменных окружения."
        )

    session = None
    if settings.PROXY_URL:
        proxy_url = settings.PROXY_URL.strip()
        parts = proxy_url.split(":")
        if len(parts) == 5 and "@" not in proxy_url:
            scheme_and_user = f"{parts[0]}:{parts[1]}"
            proxy_url = f"{scheme_and_user}:{parts[2]}@{parts[3]}:{parts[4]}"

        logger.info(f"Используется прокси для Telegram API: {_mask_proxy(proxy_url)}")
        session = AiohttpSession(proxy=proxy_url)

    bot = Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(common.router)
    dp.include_router(search.router)
    dp.include_router(compare.router)
    dp.include_router(profile.router)

    # Запуск фонового обновления цен
    asyncio.create_task(background_prices_updater())

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
