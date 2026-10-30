from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import CompareMarketsStates
from bot.keyboards.main_menu import get_cancel_kb
from bot.keyboards.search import get_stattrak_kb, get_quality_kb
from bot.keyboards.compare import (
    get_donor_markets_kb,
    get_recipient_markets_kb,
    get_compare_result_kb
)
from bot.services.market_service import get_live_comparison
from bot.services.mock_data import QUALITIES
from bot.services.calculator import calculate_arbitrage
from bot.database.db import get_or_create_user, add_deal

router = Router(name="compare")

@router.callback_query(F.data == "menu_compare")
async def start_compare(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CompareMarketsStates.waiting_for_name)
    await callback.message.edit_text(
        "<b>Сравнение 2 маркетов</b>\n\n"
        "Введите название скина (например: M4A4 | The Emperor):",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()

@router.message(CompareMarketsStates.waiting_for_name)
async def process_compare_skin_name(message: Message, state: FSMContext):
    skin_name = message.text.strip()
    if len(skin_name) < 2:
        await message.answer("Название скина слишком короткое. Введите еще раз:")
        return

    await state.update_data(skin_name=skin_name)
    await state.set_state(CompareMarketsStates.waiting_for_stattrak)

    await message.answer(
        f"Скин: <b>{skin_name}</b>\n\n"
        "Выберите тип предмета:",
        parse_mode="HTML",
        reply_markup=get_stattrak_kb(prefix="compare")
    )

@router.callback_query(CompareMarketsStates.waiting_for_stattrak, F.data.startswith("compare_st_"))
async def process_compare_stattrak(callback: CallbackQuery, state: FSMContext):
    is_stattrak = callback.data.endswith("_1")
    await state.update_data(is_stattrak=is_stattrak)
    await state.set_state(CompareMarketsStates.waiting_for_quality)

    data = await state.get_data()
    st_prefix = "StatTrak™ " if is_stattrak else ""
    full_name = f"{st_prefix}{data['skin_name']}"

    await callback.message.edit_text(
        f"Скин: <b>{full_name}</b>\n\n"
        "Выберите качество предмета:",
        parse_mode="HTML",
        reply_markup=get_quality_kb(prefix="compare")
    )
    await callback.answer()

@router.callback_query(CompareMarketsStates.waiting_for_quality, F.data.startswith("compare_q_"))
async def process_compare_quality(callback: CallbackQuery, state: FSMContext):
    quality_code = callback.data.split("_")[-1]
    await state.update_data(quality=quality_code)
    await state.set_state(CompareMarketsStates.waiting_for_donor)

    await callback.message.edit_text(
        "Выберите маркет-донор (где покупаем):",
        parse_mode="HTML",
        reply_markup=get_donor_markets_kb()
    )
    await callback.answer()

@router.callback_query(CompareMarketsStates.waiting_for_donor, F.data.startswith("donor_"))
async def process_donor_market(callback: CallbackQuery, state: FSMContext):
    donor_id = callback.data.replace("donor_", "")
    await state.update_data(donor_id=donor_id)
    await state.set_state(CompareMarketsStates.waiting_for_recipient)

    await callback.message.edit_text(
        "Выберите маркет-реципиент (где продаем):",
        parse_mode="HTML",
        reply_markup=get_recipient_markets_kb(excluded_id=donor_id)
    )
    await callback.answer()

@router.callback_query(CompareMarketsStates.waiting_for_recipient, F.data.startswith("recip_"))
async def process_recipient_market(callback: CallbackQuery, state: FSMContext):
    recipient_id = callback.data.replace("recip_", "")
    data = await state.get_data()

    skin_name = data["skin_name"]
    is_stattrak = data["is_stattrak"]
    quality_code = data["quality"]
    donor_id = data["donor_id"]

    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    deposit_fee = user.get("deposit_fee", 0.0)
    sale_fee = user.get("sale_fee", 5.0)
    withdraw_fee = user.get("withdraw_fee", 3.0)

    donor_meta, donor_offer, recip_meta, recip_offer = await get_live_comparison(
        skin_name=skin_name,
        is_stattrak=is_stattrak,
        quality=quality_code,
        donor_id=donor_id,
        recipient_id=recipient_id
    )

    calc = calculate_arbitrage(
        buy_price=donor_offer.price,
        sell_price=recip_offer.price,
        deposit_fee_percent=deposit_fee,
        sale_fee_percent=sale_fee,
        withdraw_fee_percent=withdraw_fee
    )

    await state.update_data(
        last_calc={
            "skin_name": f"{'StatTrak™ ' if is_stattrak else ''}{skin_name} ({quality_code})",
            "donor_market": donor_meta["name"],
            "recipient_market": recip_meta["name"],
            "buy_price": calc.buy_price,
            "sell_price": calc.sell_price,
            "net_profit": calc.net_profit,
            "roi": calc.roi
        }
    )

    st_prefix = "StatTrak™ " if is_stattrak else ""
    quality_name = QUALITIES.get(quality_code, quality_code)
    profit_emoji = "🟢" if calc.net_profit >= 0 else "🔴"
    profit_sign = "+" if calc.net_profit >= 0 else ""

    text = (
        f"<b>Результат сравнения:</b>\n"
        f"{st_prefix}{skin_name} ({quality_name})\n\n"
        f"Покупка ({donor_meta['name']}): {calc.buy_price:.2f} ₽\n"
        f"С учетом ввода (+{deposit_fee}%): {calc.real_cost:.2f} ₽\n\n"
        f"Продажа ({recip_meta['name']}): {calc.sell_price:.2f} ₽\n"
        f"Комиссия продажи: {sale_fee}%, вывода: {withdraw_fee}%\n"
        f"На руки: {calc.net_payout:.2f} ₽\n\n"
        f"────────────────────\n"
        f"{profit_emoji} Чистый профит: <b>{profit_sign}{calc.net_profit:.2f} ₽</b>\n"
        f"ROI: <b>{profit_sign}{calc.roi:.2f}%</b>\n"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_compare_result_kb(
            buy_url=donor_offer.item_url,
            sell_url=recip_offer.item_url
        )
    )
    await callback.answer()

@router.callback_query(F.data == "deal_save")
async def process_deal_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    last_calc = data.get("last_calc")

    if not last_calc:
        await callback.answer("Данные для сохранения устарели.", show_alert=True)
        return

    await add_deal(
        user_id=callback.from_user.id,
        skin_name=last_calc["skin_name"],
        donor_market=last_calc["donor_market"],
        recipient_market=last_calc["recipient_market"],
        buy_price=last_calc["buy_price"],
        sell_price=last_calc["sell_price"],
        net_profit=last_calc["net_profit"],
        roi=last_calc["roi"]
    )

    await callback.answer("Круг сохранен в журнал сделок!", show_alert=True)
