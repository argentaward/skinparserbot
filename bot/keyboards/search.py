from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.mock_data import MarketOffer

def get_stattrak_kb(prefix: str = "search") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🔹 Обычный", callback_data=f"{prefix}_st_0"),
            InlineKeyboardButton(text="🔸 StatTrak™", callback_data=f"{prefix}_st_1")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_quality_kb(prefix: str = "search") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="FN (Прямо с завода)", callback_data=f"{prefix}_q_FN"),
            InlineKeyboardButton(text="MW (Немного поношенное)", callback_data=f"{prefix}_q_MW"),
        ],
        [
            InlineKeyboardButton(text="FT (После полевых)", callback_data=f"{prefix}_q_FT"),
            InlineKeyboardButton(text="WW (Поношенное)", callback_data=f"{prefix}_q_WW"),
        ],
        [
            InlineKeyboardButton(text="BS (Закаленное в боях)", callback_data=f"{prefix}_q_BS")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_offers_list_kb(offers: List[MarketOffer]) -> InlineKeyboardMarkup:
    keyboard = []
    for idx, offer in enumerate(offers):
        discount_text = f" (-{int(offer.discount_percent)}%)" if offer.discount_percent > 0 else ""
        button_text = f"{offer.market_name}: {offer.price:.2f} ₽{discount_text}"
        keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"offer_view_{idx}")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🔄 Искать другой скин", callback_data="menu_search"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_offer_detail_kb(offer_url: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🔗 Перейти на маркет", url=offer_url)],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="offer_back_list")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
