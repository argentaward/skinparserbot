from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states import ProfileStates
from bot.keyboards.profile import get_profile_kb, get_fees_edit_kb, get_key_manage_kb
from bot.keyboards.main_menu import get_cancel_kb
from bot.database.db import (
    get_or_create_user,
    update_user_fees,
    get_user_deals,
    get_user_api_keys,
    set_user_api_key
)
from bot.services.crypto import mask_api_key
from bot.services.api_clients import MarketCsgoClient, LisSkinsClient

router = Router(name="profile")

async def build_profile_data(user_id: int, username: str):
    user = await get_or_create_user(user_id, username)
    deals = await get_user_deals(user_id, limit=50)
    keys = await get_user_api_keys(user_id)

    # Запрос баланса Market.CSGO
    cstm_key = keys.get("cstm")
    if cstm_key:
        ok_cstm, _, cstm_bal_text = await MarketCsgoClient.get_balance(cstm_key)
        cstm_display = f"<b>{cstm_bal_text}</b> (Ключ: <code>{mask_api_key(cstm_key)}</code>)" if ok_cstm else f"⚠️ Ошибка: {cstm_bal_text}"
    else:
        cstm_display = "Не подключен"

    # Запрос баланса Lis-Skins
    lis_key = keys.get("lis")
    if lis_key:
        ok_lis, _, lis_bal_text = await LisSkinsClient.get_balance(lis_key)
        lis_display = f"<b>{lis_bal_text}</b> (Ключ: <code>{mask_api_key(lis_key)}</code>)" if ok_lis else f"⚠️ Ошибка: {lis_bal_text}"
    else:
        lis_display = "Не подключен"

    total_deals = len(deals)
    total_profit = sum(d["net_profit"] for d in deals)
    profit_sign = "+" if total_profit >= 0 else ""

    text = (
        f"👤 <b>Личный кабинет</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Пользователь: @{user['username'] or 'не указан'}\n\n"
        f"💳 <b>Балансы на маркетах:</b>\n"
        f"• <b>Market.CSGO:</b> {cstm_display}\n"
        f"• <b>Lis-Skins:</b> {lis_display}\n\n"
        f"⚙️ <b>Ваши комиссии:</b>\n"
        f"• Пополнение: {user['deposit_fee']}%\n"
        f"• Продажа: {user['sale_fee']}%\n"
        f"• Вывод: {user['withdraw_fee']}%\n\n"
        f"📈 <b>Статистика:</b>\n"
        f"• Сделок проведено: <b>{total_deals}</b>\n"
        f"• Общий профит: <b>{profit_sign}{total_profit:.2f} ₽</b>"
    )

    kb = get_profile_kb(has_cstm=bool(cstm_key), has_lis=bool(lis_key))
    return text, kb

@router.callback_query(F.data.in_(["menu_profile", "profile_refresh_balances"]))
async def show_profile(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = await build_profile_data(callback.from_user.id, callback.from_user.username)
    
    try:
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception:
        pass
    await callback.answer("Балансы обновлены" if callback.data == "profile_refresh_balances" else None)

# --- Управление ключом Market.CSGO ---
@router.callback_query(F.data == "key_manage_cstm")
async def manage_cstm_key(callback: CallbackQuery):
    keys = await get_user_api_keys(callback.from_user.id)
    cstm_key = keys.get("cstm")
    status = f"Подключен ({mask_api_key(cstm_key)})" if cstm_key else "Не привязан"

    text = (
        "🔑 <b>Управление ключом Market.CSGO (cstm)</b>\n\n"
        f"Текущий статус: <b>{status}</b>\n\n"
        "📌 <i>Где найти ключ:</i>\n"
        "Зайдите на сайт <b>market.csgo.com</b> ➡️ Настройки ➡️ блок «API ключ».\n\n"
        "🔒 <i>Безопасность:</i>\n"
        "Ключ хранится в зашифрованном виде (AES-256) и используется исключительно для проверки баланса и быстрых покупок скинов на ваш аккаунт."
    )
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_key_manage_kb("cstm", is_bound=bool(cstm_key))
    )
    await callback.answer()

@router.callback_query(F.data == "key_input_cstm")
async def prompt_cstm_key(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_cstm_key)
    await callback.message.edit_text(
        "Введите ваш <b>API-ключ Market.CSGO</b> сообщением в чат:\n\n"
        "<i>(Сообщение с ключом будет сразу автоматически удалено ботом для безопасности)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()

@router.message(ProfileStates.waiting_for_cstm_key)
async def process_cstm_key(message: Message, state: FSMContext):
    raw_key = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass

    if len(raw_key) < 10:
        await message.answer("Слишком короткий ключ. Проверьте правильность и отправьте еще раз:")
        return

    # Проверка ключа через реальный API
    status_msg = await message.answer("🔄 Проверяю API-ключ в Market.CSGO...")
    ok, _, res_text = await MarketCsgoClient.get_balance(raw_key)

    if not ok:
        await status_msg.edit_text(
            f"❌ <b>Ошибка валидации ключа:</b> {res_text}\n\n"
            "Убедитесь, что вы скопировали правильный API-ключ в личном кабинете market.csgo.com.",
            parse_mode="HTML",
            reply_markup=get_key_manage_kb("cstm", is_bound=False)
        )
        return

    await set_user_api_key(message.from_user.id, "cstm", raw_key)
    await state.clear()
    text, kb = await build_profile_data(message.from_user.id, message.from_user.username)
    await status_msg.edit_text(
        f"✅ <b>API-ключ Market.CSGO успешно подключен!</b>\n\n"
        f"Баланс: <b>{res_text}</b>\n\n" + text,
        parse_mode="HTML",
        reply_markup=kb
    )

@router.callback_query(F.data == "key_delete_cstm")
async def delete_cstm_key(callback: CallbackQuery):
    await set_user_api_key(callback.from_user.id, "cstm", None)
    await callback.answer("Ключ Market.CSGO удален")
    text, kb = await build_profile_data(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=kb)

# --- Управление ключом Lis-Skins ---
@router.callback_query(F.data == "key_manage_lis")
async def manage_lis_key(callback: CallbackQuery):
    keys = await get_user_api_keys(callback.from_user.id)
    lis_key = keys.get("lis")
    status = f"Подключен ({mask_api_key(lis_key)})" if lis_key else "Не привязан"

    text = (
        "🔑 <b>Управление ключом Lis-Skins</b>\n\n"
        f"Текущий статус: <b>{status}</b>\n\n"
        "📌 <i>Где найти ключ:</i>\n"
        "Зайдите на сайт <b>lis-skins.ru</b> ➡️ Профиль ➡️ раздел API (создайте токен доступа).\n\n"
        "🔒 <i>Безопасность:</i>\n"
        "Ключ хранится в зашифрованном виде (AES-256) и используется для просмотра баланса и покупки."
    )
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_key_manage_kb("lis", is_bound=bool(lis_key))
    )
    await callback.answer()

@router.callback_query(F.data == "key_input_lis")
async def prompt_lis_key(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_lis_key)
    await callback.message.edit_text(
        "Введите ваш <b>API-ключ (токен) Lis-Skins</b> сообщением в чат:\n\n"
        "<i>(Сообщение будет сразу удалено ботом для конфиденциальности)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()

@router.message(ProfileStates.waiting_for_lis_key)
async def process_lis_key(message: Message, state: FSMContext):
    raw_key = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass

    if len(raw_key) < 10:
        await message.answer("Слишком короткий ключ. Проверьте правильность и отправьте еще раз:")
        return

    status_msg = await message.answer("🔄 Проверяю API-ключ в Lis-Skins...")
    ok, _, res_text = await LisSkinsClient.get_balance(raw_key)

    if not ok:
        await status_msg.edit_text(
            f"❌ <b>Ошибка валидации ключа:</b> {res_text}\n\n"
            "Убедитесь, что токен активен в профиле lis-skins.ru.",
            parse_mode="HTML",
            reply_markup=get_key_manage_kb("lis", is_bound=False)
        )
        return

    await set_user_api_key(message.from_user.id, "lis", raw_key)
    await state.clear()
    text, kb = await build_profile_data(message.from_user.id, message.from_user.username)
    await status_msg.edit_text(
        f"✅ <b>API-ключ Lis-Skins успешно подключен!</b>\n\n"
        f"Баланс: <b>{res_text}</b>\n\n" + text,
        parse_mode="HTML",
        reply_markup=kb
    )

@router.callback_query(F.data == "key_delete_lis")
async def delete_lis_key(callback: CallbackQuery):
    await set_user_api_key(callback.from_user.id, "lis", None)
    await callback.answer("Ключ Lis-Skins удален")
    text, kb = await build_profile_data(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=kb)

# --- Настройка комиссий ---
@router.callback_query(F.data == "profile_edit_fees")
async def edit_fees_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ <b>Настройка комиссий</b>\n\n"
        "Выберите комиссию для изменения:",
        parse_mode="HTML",
        reply_markup=get_fees_edit_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "fee_edit_dep")
async def ask_dep_fee(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_deposit_fee)
    await callback.message.edit_text(
        "Введите новый процент комиссии на пополнение (например: 1.5 или 0):",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "fee_edit_sale")
async def ask_sale_fee(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_sale_fee)
    await callback.message.edit_text(
        "Введите новый процент комиссии маркета за продажу (например: 5.0):",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "fee_edit_with")
async def ask_with_fee(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_withdraw_fee)
    await callback.message.edit_text(
        "Введите новый процент комиссии на вывод средств (например: 5.0):",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()

@router.message(ProfileStates.waiting_for_deposit_fee)
async def save_dep_fee(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError()
    except ValueError:
        await message.answer("Введите корректное число от 0 до 100:")
        return

    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await update_user_fees(message.from_user.id, val, user["sale_fee"], user["withdraw_fee"])
    await state.clear()
    text, kb = await build_profile_data(message.from_user.id, message.from_user.username)
    await message.answer(f"✅ Комиссия пополнения обновлена: <b>{val}%</b>\n\n" + text, parse_mode="HTML", reply_markup=kb)

@router.message(ProfileStates.waiting_for_sale_fee)
async def save_sale_fee(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError()
    except ValueError:
        await message.answer("Введите корректное число от 0 до 100:")
        return

    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await update_user_fees(message.from_user.id, user["deposit_fee"], val, user["withdraw_fee"])
    await state.clear()
    text, kb = await build_profile_data(message.from_user.id, message.from_user.username)
    await message.answer(f"✅ Комиссия продажи обновлена: <b>{val}%</b>\n\n" + text, parse_mode="HTML", reply_markup=kb)

@router.message(ProfileStates.waiting_for_withdraw_fee)
async def save_with_fee(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError()
    except ValueError:
        await message.answer("Введите корректное число от 0 до 100:")
        return

    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await update_user_fees(message.from_user.id, user["deposit_fee"], user["sale_fee"], val)
    await state.clear()
    text, kb = await build_profile_data(message.from_user.id, message.from_user.username)
    await message.answer(f"✅ Комиссия вывода обновлена: <b>{val}%</b>\n\n" + text, parse_mode="HTML", reply_markup=kb)

# --- Журнал сделок ---
@router.callback_query(F.data == "profile_deals_history")
async def show_deals_history(callback: CallbackQuery):
    deals = await get_user_deals(callback.from_user.id, limit=10)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="menu_profile")]
    ])

    if not deals:
        await callback.message.edit_text(
            "📜 <b>Журнал сделок пуст</b>\n\n"
            "Вы еще не записали ни одного торгового круга. Проведите сравнение в меню «Сравнение 2 маркетов» и нажмите «Круг проведен».",
            parse_mode="HTML",
            reply_markup=back_kb
        )
        await callback.answer()
        return

    lines = ["📜 <b>Последние 10 торговых кругов:</b>\n"]
    for i, d in enumerate(deals, start=1):
        sign = "+" if d["net_profit"] >= 0 else ""
        date_str = d["created_at"][:16] if d.get("created_at") else ""
        lines.append(
            f"<b>{i}. {d['skin_name']}</b> ({date_str})\n"
            f"   {d['donor_market']} ➡️ {d['recipient_market']}\n"
            f"   Куплено: {d['buy_price']} ₽ | Продано: {d['sell_price']} ₽\n"
            f"   Итог: <b>{sign}{d['net_profit']:.2f} ₽</b> (ROI: <b>{sign}{d['roi']:.1f}%</b>)\n"
        )

    await callback.message.edit_text(
        text="\n".join(lines),
        parse_mode="HTML",
        reply_markup=back_kb
    )
    await callback.answer()
