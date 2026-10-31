import logging
from typing import Tuple, Optional
import aiohttp

logger = logging.getLogger("api_clients")

class MarketCsgoClient:
    BASE_URL = "https://market.csgo.com/api/v2"

    @classmethod
    async def get_balance(cls, api_key: str) -> Tuple[bool, float, str]:
        """
        Возвращает (success, balance_rub, message).
        """
        if not api_key:
            return False, 0.0, "API-ключ не указан"

        url = f"{cls.BASE_URL}/get-money?key={api_key.strip()}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SkinParserBot/1.0"
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("success"):
                        money = float(data.get("money", 0.0))
                        currency = data.get("currency", "RUB")
                        return True, money, f"{money:,.2f} {currency}".replace(",", " ")
                    
                    err = data.get("error", f"Ошибка HTTP {resp.status}")
                    return False, 0.0, err
        except Exception as e:
            logger.error(f"Ошибка запроса баланса Market.CSGO: {e}")
            return False, 0.0, "Ошибка подключения к Market.CSGO"


class LisSkinsClient:
    BASE_URL = "https://api.lis-skins.com/v1"

    @classmethod
    async def get_balance(cls, api_key: str) -> Tuple[bool, float, str]:
        """
        Возвращает (success, balance_rub, message).
        """
        if not api_key:
            return False, 0.0, "API-ключ не указан"

        url = f"{cls.BASE_URL}/user/balance"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SkinParserBot/1.0"
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        balance = float(data.get("balance", data.get("data", {}).get("balance", 0.0)))
                        return True, balance, f"{balance:,.2f} ₽".replace(",", " ")
                    elif resp.status == 403:
                        return False, 0.0, "Неверный API-ключ Lis-Skins"
                    else:
                        text = await resp.text()
                        return False, 0.0, f"Ошибка Lis-Skins: {resp.status}"
        except Exception as e:
            logger.error(f"Ошибка запроса баланса Lis-Skins: {e}")
            return False, 0.0, "Ошибка подключения к Lis-Skins"
