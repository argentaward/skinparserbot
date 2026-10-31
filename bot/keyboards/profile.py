from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_profile_kb(has_cstm: bool = False, has_lis: bool = False) -> InlineKeyboardMarkup:
    cstm_btn = "🔑 CSTM: Подключен" if has_cstm else "➕ Привязать Market.CSGO"
    lis_btn = "🔑 Lis-Skins: Подключен" if has_lis else "➕ Привязать Lis-Skins"
    
    keyboard = [
        [InlineKeyboardButton(text="🔄 Обновить балансы", callback_data="profile_refresh_balances")],
        [
            InlineKeyboardButton(text=cstm_btn, callback_data="key_manage_cstm"),
            InlineKeyboardButton(text=lis_btn, callback_data="key_manage_lis"),
        ],
        [InlineKeyboardButton(text="⚙️ Настроить комиссии", callback_data="profile_edit_fees")],
        [InlineKeyboardButton(text="📜 Журнал сделок", callback_data="profile_deals_history")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_key_manage_kb(market: str, is_bound: bool) -> InlineKeyboardMarkup:
    keyboard = []
    if is_bound:
        keyboard.append([InlineKeyboardButton(text="✏️ Изменить API-ключ", callback_data=f"key_input_{market}")])
        keyboard.append([InlineKeyboardButton(text="❌ Отвязать и удалить ключ", callback_data=f"key_delete_{market}")])
    else:
        keyboard.append([InlineKeyboardButton(text="➕ Ввести API-ключ", callback_data=f"key_input_{market}")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="menu_profile")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_fees_edit_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="1️⃣ Комиссия пополнения (%)", callback_data="fee_edit_dep")],
        [InlineKeyboardButton(text="2️⃣ Комиссия продажи (%)", callback_data="fee_edit_sale")],
        [InlineKeyboardButton(text="3️⃣ Комиссия вывода (%)", callback_data="fee_edit_with")],
        [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="menu_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
