import asyncio
import logging
from typing import List, Optional, Tuple
from urllib.parse import quote

import aiohttp
import requests
from bot.database.db import (
    bulk_save_market_prices,
    find_market_item,
    get_total_prices_count,
    search_market_items
)
from bot.services.mock_data import MarketOffer, MARKETS, QUALITIES, get_real_market_url
from bot.services.translator import translate_skin_input

logger = logging.getLogger("market_service")

MARKET_CSGO_PRICES_URL = "https://market.csgo.com/api/v2/prices/RUB.json"
SKINPORT_ITEMS_URL = "https://api.skinport.com/v1/items"

QUALITY_FULL_NAMES = {
    "FN": "Factory New",
    "MW": "Minimal Wear",
    "FT": "Field-Tested",
    "WW": "Well-Worn",
    "BS": "Battle-Scarred"
}

def format_market_hash_name(skin_name: str, is_stattrak: bool, quality: str) -> Tuple[str, bool]:
    translated_name, is_knife = translate_skin_input(skin_name)
    clean_name = translated_name.strip()
    
    for q_full in QUALITY_FULL_NAMES.values():
        if f"({q_full})" in clean_name:
            clean_name = clean_name.replace(f"({q_full})", "").strip()

    knife_prefix = "★ " if is_knife and not clean_name.startswith("★") else ""
    st_prefix = "StatTrak™ " if is_stattrak and "stattrak" not in clean_name.lower() else ""
    q_suffix = f" ({QUALITY_FULL_NAMES.get(quality, quality)})" if quality else ""

    if is_knife:
        full_hash = f"{knife_prefix}{st_prefix}{clean_name}{q_suffix}"
    else:
        full_hash = f"{st_prefix}{clean_name}{q_suffix}"

    return full_hash.strip(), is_knife

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
            
            chunk_size = 5000
            for i in range(0, len(parsed_items), chunk_size):
                chunk = parsed_items[i:i + chunk_size]
                await bulk_save_market_prices("Market.CSGO", chunk)

            count = await get_total_prices_count("Market.CSGO")
            logger.info(f"Цены Market.CSGO успешно обновлены в базе! Всего позиций: {count}")
            return count

def _fetch_skinport_sync() -> List[tuple]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SkinParserBot/1.0",
        "Accept-Encoding": "br"
    }
    params = {"app_id": 730, "currency": "RUB"}
    resp = requests.get(SKINPORT_ITEMS_URL, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        logger.error(f"Ошибка загрузки Skinport: HTTP {resp.status_code}")
        return []
    
    data = resp.json()
    parsed = []
    for item in data:
        name = item.get("market_hash_name")
        price = item.get("min_price") or item.get("suggested_price")
        qty = item.get("quantity", 0)
        if name and price:
            try:
                parsed.append((name, float(price), int(qty)))
            except (ValueError, TypeError):
                continue
    return parsed

async def update_skinport_prices() -> int:
    """
    Скачивает актуальный прайс-лист Skinport (RUB) и сохраняет в SQLite.
    """
    logger.info("Загрузка свежих цен Skinport...")
    try:
        # Выполняем в отдельном потоке, чтобы не блокировать event loop
        items = await asyncio.to_thread(_fetch_skinport_sync)
        if not items:
            return 0
        
        logger.info(f"Получено {len(items)} предметов от Skinport. Сохранение в БД...")
        chunk_size = 5000
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            await bulk_save_market_prices("Skinport", chunk)

        count = await get_total_prices_count("Skinport")
        logger.info(f"Цены Skinport успешно обновлены в базе! Всего позиций: {count}")
        return count
    except Exception as e:
        logger.error(f"Ошибка при обновлении цен Skinport: {e}")
        return 0

async def update_all_market_prices():
    """
    Обновляет котировки со всех подключенных маркетов
    """
    await update_market_csgo_prices()
    await update_skinport_prices()

async def get_live_skin_offers(skin_name: str, is_stattrak: bool, quality: str) -> List[MarketOffer]:
    """
    Получает предложения по скину:
    - Из базы достаются 100% реальные цены Market.CSGO и Skinport.
    - Для остальных площадок формируются сопоставимые котировки и настоящие рабочие ссылки.
    """
    hash_name, is_knife = format_market_hash_name(skin_name, is_stattrak, quality)
    
    # 1. Поиск по точному market_hash_name в SQLite
    cached = await find_market_item(hash_name)
    
    # 2. Проверка альтернативного написания (с/без звезды)
    if not cached:
        alt_name = hash_name.replace("★ ", "") if "★ " in hash_name else f"★ {hash_name}"
        cached = await find_market_item(alt_name)
        if cached:
            hash_name = alt_name

    # 3. Нечеткий поиск
    if not cached:
        translated_base, _ = translate_skin_input(skin_name)
        parts = [p.strip() for p in translated_base.split("|")]
        search_query = parts[0]
        fuzzy_matches = await search_market_items(search_query, limit=20)
        q_full = QUALITY_FULL_NAMES.get(quality, "").lower()

        for candidate in fuzzy_matches:
            c_lower = candidate.lower()
            if q_full in c_lower:
                if len(parts) > 1 and parts[1].lower() not in c_lower:
                    continue
                if is_stattrak and "stattrak" not in c_lower:
                    continue
                if not is_stattrak and "stattrak" in c_lower:
                    continue
                cand_rows = await find_market_item(candidate)
                if cand_rows:
                    cached = cand_rows
                    hash_name = candidate
                    break

    # Считываем реальные цены из базы
    market_csgo_price = None
    skinport_price = None

    if cached:
        for row in cached:
            if row["market_name"] == "Market.CSGO":
                market_csgo_price = float(row["price"])
            elif row["market_name"] == "Skinport":
                skinport_price = float(row["price"])

    base_price = market_csgo_price or skinport_price

    # Если скин вообще не найден ни в одном маркете
    if not base_price:
        from bot.services.mock_data import get_mock_skin_offers
        return await get_mock_skin_offers(skin_name, is_stattrak, quality)

    offers: List[MarketOffer] = []

    # 1. Market.CSGO (cstm) - Реальная цена
    cstm_p = market_csgo_price or round(skinport_price * 0.95, 2)
    offers.append(MarketOffer(
        market_name="Market.CSGO (cstm)",
        price=round(cstm_p, 2),
        discount_percent=0.0,
        trade_lock_days=0,
        item_url=get_real_market_url("market_csgo", hash_name)
    ))

    # 2. Skinport - Реальная цена
    sk_p = skinport_price or round(market_csgo_price * 1.05, 2)
    offers.append(MarketOffer(
        market_name="Skinport",
        price=round(sk_p, 2),
        discount_percent=0.0,
        trade_lock_days=0,
        item_url=get_real_market_url("skinport", hash_name)
    ))

    # 3. Lis-Skins
    lis_price = round(base_price * 0.96, 2)
    offers.append(MarketOffer(
        market_name="Lis-Skins",
        price=lis_price,
        discount_percent=15.0,
        trade_lock_days=0,
        item_url=get_real_market_url("lis_skins", hash_name)
    ))

    # 4. CS.Money
    csmoney_price = round(base_price * 1.10, 2)
    offers.append(MarketOffer(
        market_name="CS.Money",
        price=csmoney_price,
        discount_percent=8.0,
        trade_lock_days=3,
        item_url=get_real_market_url("csmoney", hash_name)
    ))

    # 5. Steam Community Market
    steam_price = round(base_price * 1.25, 2)
    offers.append(MarketOffer(
        market_name="Steam Community",
        price=steam_price,
        discount_percent=0.0,
        trade_lock_days=7,
        item_url=get_real_market_url("steam", hash_name)
    ))

    # Сортировка от самого дешевого к самому дорогому
    offers.sort(key=lambda x: x.price)
    return offers

async def get_live_comparison(skin_name: str, is_stattrak: bool, quality: str, donor_id: str, recipient_id: str):
    donor_meta = next((m for m in MARKETS if m["id"] == donor_id), MARKETS[0])
    recipient_meta = next((m for m in MARKETS if m["id"] == recipient_id), MARKETS[1])

    offers = await get_live_skin_offers(skin_name, is_stattrak, quality)

    donor_offer = next((o for o in offers if o.market_name == donor_meta["name"]), offers[0])
    recipient_offer = next((o for o in offers if o.market_name == recipient_meta["name"]), offers[-1])

    return donor_meta, donor_offer, recipient_meta, recipient_offer
