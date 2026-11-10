from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_profile_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="⚙️ Настроить комиссии", callback_data="profile_edit_fees")],
        [InlineKeyboardButton(text="📜 Журнал сделок", callback_data="profile_deals_history")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_fees_edit_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="1️⃣ Комиссия пополнения (%)", callback_data="fee_edit_dep")],
        [InlineKeyboardButton(text="2️⃣ Комиссия продажи (%)", callback_data="fee_edit_sale")],
        [InlineKeyboardButton(text="3️⃣ Комиссия вывода (%)", callback_data="fee_edit_with")],
        [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="menu_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
