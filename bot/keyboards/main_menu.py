from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🔍 Поиск скина", callback_data="menu_search")],
        [InlineKeyboardButton(text="🔄 Сравнение 2 маркетов", callback_data="menu_compare")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена / В главное меню", callback_data="menu_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
