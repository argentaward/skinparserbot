from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import ProfileStates
from bot.keyboards.profile import get_profile_kb, get_fees_edit_kb
from bot.keyboards.main_menu import get_cancel_kb
from bot.database.db import get_or_create_user, update_user_fees, get_user_deals

router = Router(name="profile")

@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    deals = await get_user_deals(callback.from_user.id, limit=50)

    total_deals = len(deals)
    total_profit = sum(d["net_profit"] for d in deals)
    profit_sign = "+" if total_profit >= 0 else ""

    text = (
        f"👤 <b>Личный кабинет</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Пользователь: @{user['username'] or 'не указан'}\n\n"
        f"⚙️ <b>Комиссии:</b>\n"
        f"• Пополнение: {user['deposit_fee']}%\n"
        f"• Продажа: {user['sale_fee']}%\n"
        f"• Вывод: {user['withdraw_fee']}%\n\n"
        f"📈 <b>Статистика:</b>\n"
        f"• Сделок проведено: <b>{total_deals}</b>\n"
        f"• Общий профит: <b>{profit_sign}{total_profit:.2f} ₽</b>\n"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_profile_kb()
    )
    await callback.answer()

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
        "Введите новый процент комиссии на вывод средств (например: 3.0):",
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
    await message.answer(f"✅ Комиссия пополнения обновлена: <b>{val}%</b>", parse_mode="HTML", reply_markup=get_profile_kb())

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
    await message.answer(f"✅ Комиссия маркета обновлена: <b>{val}%</b>", parse_mode="HTML", reply_markup=get_profile_kb())

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
    await message.answer(f"✅ Комиссия вывода обновлена: <b>{val}%</b>", parse_mode="HTML", reply_markup=get_profile_kb())

@router.callback_query(F.data == "profile_deals_history")
async def show_deals_history(callback: CallbackQuery):
    deals = await get_user_deals(callback.from_user.id, limit=10)

    if not deals:
        await callback.message.edit_text(
            "📜 <b>Журнал сделок пуст.</b>\n\n"
            "После проведения и сравнения кругов нажимайте «Круг проведен», чтобы сохранять их сюда.",
            parse_mode="HTML",
            reply_markup=get_profile_kb()
        )
        await callback.answer()
        return

    lines = ["📜 <b>Последние сделки:</b>\n"]
    for i, d in enumerate(deals, start=1):
        sign = "+" if d["net_profit"] >= 0 else ""
        lines.append(
            f"{i}. <b>{d['skin_name']}</b>\n"
            f"   {d['donor_market']} ➡️ {d['recipient_market']}\n"
            f"   Покупка: {d['buy_price']:.2f} ₽ | Продажа: {d['sell_price']:.2f} ₽\n"
            f"   Итог: <b>{sign}{d['net_profit']:.2f} ₽</b> (ROI: {sign}{d['roi']:.2f}%)\n"
            f"   <i>Дата: {d['created_at']}</i>\n"
        )

    await callback.message.edit_text(
        text="\n".join(lines),
        parse_mode="HTML",
        reply_markup=get_profile_kb()
    )
    await callback.answer()
