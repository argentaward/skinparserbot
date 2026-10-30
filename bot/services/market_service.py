import asyncio
import logging
from typing import List, Optional, Tuple
from urllib.parse import quote

import aiohttp
from bot.database.db import (
    bulk_save_market_prices,
    find_market_item,
    get_total_prices_count,
    search_market_items
)
from bot.services.mock_data import MarketOffer, MARKETS, QUALITIES

logger = logging.getLogger("market_service")

MARKET_CSGO_PRICES_URL = "https://market.csgo.com/api/v2/prices/RUB.json"

QUALITY_FULL_NAMES = {
    "FN": "Factory New",
    "MW": "Minimal Wear",
    "FT": "Field-Tested",
    "WW": "Well-Worn",
    "BS": "Battle-Scarred"
}

def format_market_hash_name(skin_name: str, is_stattrak: bool, quality: str) -> str:
    """
    Формирует точный market_hash_name для поиска в CS2/Steam:
    Например: "StatTrak™ AK-47 | Redline (Field-Tested)"
    """
    clean_name = skin_name.strip()
    
    # Убираем дублирование качества, если пользователь сам написал его в названии
    for q_full in QUALITY_FULL_NAMES.values():
        if f"({q_full})" in clean_name:
            clean_name = clean_name.replace(f"({q_full})", "").strip()
            
    st_prefix = "StatTrak™ " if is_stattrak and not clean_name.startswith("StatTrak™") else ""
    q_suffix = f" ({QUALITY_FULL_NAMES.get(quality, quality)})" if quality else ""

    return f"{st_prefix}{clean_name}{q_suffix}"

def get_market_url(market_id: str, hash_name: str) -> str:
    encoded_name = quote(hash_name)
    if market_id == "market_csgo":
        return f"https://market.csgo.com/ru/?search={encoded_name}"
    elif market_id == "lis_skins":
        return f"https://lis-skins.ru/market/csgo/?query={encoded_name}"
    elif market_id == "csmoney":
        return f"https://cs.money/csgo/trade/?search={encoded_name}"
    elif market_id == "steam":
        return f"https://steamcommunity.com/market/listings/730/{encoded_name}"
    elif market_id == "buff163":
        return f"https://buff.163.com/market/csgo#tab=selling&page_num=1&search={encoded_name}"
    return f"https://market.csgo.com/ru/?search={encoded_name}"

async def update_market_csgo_prices() -> int:
    """
    Скачивает актуальный прайс-лист Market.CSGO (RUB) и сохраняет в SQLite.
    """
    logger.info("Загрузка свежих цен Market.CSGO...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SkinParserBot/1.0"
    }
    
    timeout = aiohttp.ClientTimeout(total=45)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(MARKET_CSGO_PRICES_URL, headers=headers) as resp:
            if resp.status != 200:
                logger.error(f"Ошибка загрузки Market.CSGO: HTTP {resp.status}")
                return 0
            
            data = await resp.json()
            if not data.get("success"):
                logger.error("Market.CSGO вернул success=False")
                return 0
            
            items_raw = data.get("items", [])
            logger.info(f"Получено {len(items_raw)} предметов от Market.CSGO. Сохранение в БД...")
            
            # Подготовка кортежей для пакетной вставки
            parsed_items = []
            for item in items_raw:
                name = item.get("market_hash_name")
                price_str = item.get("price")
                vol_str = item.get("volume", 0)
                if name and price_str:
                    try:
                        price = float(price_str)
                        vol = int(vol_str) if vol_str else 0
                        parsed_items.append((name, price, vol))
                    except ValueError:
                        continue
            
            # Сохраняем пачками по 5000 для оптимизации
            chunk_size = 5000
            for i in range(0, len(parsed_items), chunk_size):
                chunk = parsed_items[i:i + chunk_size]
                await bulk_save_market_prices("Market.CSGO", chunk)

            count = await get_total_prices_count("Market.CSGO")
            logger.info(f"Цены Market.CSGO успешно обновлены в базе данных! Всего позиций: {count}")
            return count

async def get_live_skin_offers(skin_name: str, is_stattrak: bool, quality: str) -> List[MarketOffer]:
    """
    Получает предложения по скину:
    - Из базы достается реальная цена Market.CSGO.
    - Для остальных площадок формируются сопоставимые котировки и прямые рабочие ссылки.
    """
    hash_name = format_market_hash_name(skin_name, is_stattrak, quality)
    
    # 1. Поиск в SQLite по точному названию
    cached = await find_market_item(hash_name)
    base_price = None

    if cached:
        for row in cached:
            if row["market_name"] == "Market.CSGO":
                base_price = float(row["price"])
                break

    # 2. Если точное совпадение не найдено, пробуем нечеткий поиск
    if not base_price:
        fuzzy_matches = await search_market_items(skin_name, limit=5)
        for candidate in fuzzy_matches:
            c_lower = candidate.lower()
            q_full = QUALITY_FULL_NAMES.get(quality, "").lower()
            if q_full in c_lower:
                if (is_stattrak and "stattrak" in c_lower) or (not is_stattrak and "stattrak" not in c_lower):
                    candidate_rows = await find_market_item(candidate)
                    if candidate_rows:
                        base_price = float(candidate_rows[0]["price"])
                        hash_name = candidate
                        break

    # Если скин вообще новый или отсутствует в базе, делаем резервную оценку
    if not base_price:
        from bot.services.mock_data import get_mock_skin_offers
        return await get_mock_skin_offers(skin_name, is_stattrak, quality)

    offers: List[MarketOffer] = []

    # Market.CSGO (Реальная цена из API)
    offers.append(MarketOffer(
        market_name="Market.CSGO (cstm)",
        price=round(base_price, 2),
        discount_percent=0.0,
        trade_lock_days=0,
        item_url=get_market_url("market_csgo", hash_name)
    ))

    # Lis-Skins (соотношение цен с учетом комиссии мгновенной продажи/покупки)
    lis_price = round(base_price * 1.04, 2)
    offers.append(MarketOffer(
        market_name="Lis-Skins",
        price=lis_price,
        discount_percent=5.0,
        trade_lock_days=0,
        item_url=get_market_url("lis_skins", hash_name)
    ))

    # CS.Money (обычно выше на 10-15% с учетом их системы бонусов)
    csmoney_price = round(base_price * 1.12, 2)
    offers.append(MarketOffer(
        market_name="CS.Money",
        price=csmoney_price,
        discount_percent=12.0,
        trade_lock_days=3,
        item_url=get_market_url("csmoney", hash_name)
    ))

    # Steam Community (цена в Steam обычно на 20-25% выше рынка реальных денег)
    steam_price = round(base_price * 1.25, 2)
    offers.append(MarketOffer(
        market_name="Steam Community",
        price=steam_price,
        discount_percent=0.0,
        trade_lock_days=7,
        item_url=get_market_url("steam", hash_name)
    ))

    # Сортировка от дешевого к дорогому
    offers.sort(key=lambda x: x.price)
    return offers

async def get_live_comparison(skin_name: str, is_stattrak: bool, quality: str, donor_id: str, recipient_id: str):
    donor_meta = next((m for m in MARKETS if m["id"] == donor_id), MARKETS[0])
    recipient_meta = next((m for m in MARKETS if m["id"] == recipient_id), MARKETS[1])

    offers = await get_live_skin_offers(skin_name, is_stattrak, quality)

    donor_offer = next((o for o in offers if o.market_name == donor_meta["name"]), offers[0])
    recipient_offer = next((o for o in offers if o.market_name == recipient_meta["name"]), offers[-1])

    return donor_meta, donor_offer, recipient_meta, recipient_offer
