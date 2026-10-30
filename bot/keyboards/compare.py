from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.mock_data import MARKETS

def get_donor_markets_kb() -> InlineKeyboardMarkup:
    keyboard = []
    for m in MARKETS:
        keyboard.append([
            InlineKeyboardButton(text=m['name'], callback_data=f"donor_{m['id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="menu_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_recipient_markets_kb(excluded_id: Optional[str] = None) -> InlineKeyboardMarkup:
    keyboard = []
    for m in MARKETS:
        if m["id"] == excluded_id:
            continue
        keyboard.append([
            InlineKeyboardButton(text=m['name'], callback_data=f"recip_{m['id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="menu_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_compare_result_kb(buy_url: str, sell_url: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="Купить", url=buy_url),
            InlineKeyboardButton(text="Продать", url=sell_url)
        ],
        [
            InlineKeyboardButton(text="Круг проведен (записать)", callback_data="deal_save")
        ],
        [
            InlineKeyboardButton(text="Новое сравнение", callback_data="menu_compare"),
            InlineKeyboardButton(text="Главное меню", callback_data="menu_cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
