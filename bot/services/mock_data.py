import random
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

@dataclass
class MarketOffer:
    market_name: str
    price: float
    discount_percent: float
    trade_lock_days: int
    item_url: str

MARKETS = [
    {"id": "market_csgo", "name": "Market.CSGO (cstm)", "sale_fee": 5.0, "withdraw_fee": 3.0, "deposit_fee": 0.0},
    {"id": "skinport", "name": "Skinport", "sale_fee": 12.0, "withdraw_fee": 0.0, "deposit_fee": 0.0},
    {"id": "lis_skins", "name": "Lis-Skins", "sale_fee": 7.0, "withdraw_fee": 2.5, "deposit_fee": 0.0},
    {"id": "csmoney", "name": "CS.Money", "sale_fee": 7.0, "withdraw_fee": 0.0, "deposit_fee": 0.0},
    {"id": "steam", "name": "Steam Community", "sale_fee": 13.04, "withdraw_fee": 0.0, "deposit_fee": 0.0},
]

QUALITIES = {
    "FN": "Прямо с завода (Factory New)",
    "MW": "Немного поношенное (Minimal Wear)",
    "FT": "После полевых испытаний (Field-Tested)",
    "WW": "Поношенное (Well-Worn)",
    "BS": "Закаленное в боях (Battle-Scarred)",
}

def get_real_market_url(market_id: str, query: str) -> str:
    encoded = quote(query)
    if "market_csgo" in market_id:
        return f"https://market.csgo.com/ru/?search={encoded}"
    elif "skinport" in market_id:
        return f"https://skinport.com/ru/market?search={encoded}"
    elif "lis_skins" in market_id:
        return f"https://lis-skins.ru/market/csgo/?query={encoded}"
    elif "csmoney" in market_id:
        return f"https://cs.money/csgo/trade/?search={encoded}"
    elif "steam" in market_id:
        return f"https://steamcommunity.com/market/search?appid=730&q={encoded}"
    return f"https://market.csgo.com/ru/?search={encoded}"

async def get_mock_skin_offers(skin_name: str, is_stattrak: bool, quality: str) -> List[MarketOffer]:
    seed = sum(ord(c) for c in skin_name) + (1000 if is_stattrak else 0)
    rng = random.Random(seed)
    
    base_price = rng.randint(2500, 25000)
    
    quality_mult = {
        "FN": 1.6,
        "MW": 1.25,
        "FT": 1.0,
        "WW": 0.85,
        "BS": 0.75
    }.get(quality, 1.0)
    
    if is_stattrak:
        base_price *= 1.35

    base_price *= quality_mult

    offers = []
    for m in MARKETS:
        fluctuation = rng.uniform(-0.10, 0.18)
        price = round(base_price * (1.0 + fluctuation), 2)
        discount = round(rng.uniform(0, 15), 0) if rng.random() > 0.5 else 0.0
        trade_lock = rng.choice([0, 1, 2, 3, 5, 7])
        url = get_real_market_url(m["id"], skin_name)

        offers.append(MarketOffer(
            market_name=m["name"],
            price=price,
            discount_percent=discount,
            trade_lock_days=trade_lock,
            item_url=url
        ))

    offers.sort(key=lambda x: x.price)
    return offers

async def get_mock_comparison(skin_name: str, is_stattrak: bool, quality: str, donor_id: str, recipient_id: str):
    donor_meta = next((m for m in MARKETS if m["id"] == donor_id), MARKETS[0])
    recipient_meta = next((m for m in MARKETS if m["id"] == recipient_id), MARKETS[1])
    
    all_offers = await get_mock_skin_offers(skin_name, is_stattrak, quality)
    
    donor_offer = next((o for o in all_offers if o.market_name == donor_meta["name"]), all_offers[0])
    recipient_offer = next((o for o in all_offers if o.market_name == recipient_meta["name"]), all_offers[-1])

    return donor_meta, donor_offer, recipient_meta, recipient_offer
