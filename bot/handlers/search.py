from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import SearchSkinStates
from bot.keyboards.main_menu import get_cancel_kb
from bot.keyboards.search import (
    get_stattrak_kb,
    get_quality_kb,
    get_offers_list_kb,
    get_offer_detail_kb
)
from bot.services.mock_data import get_mock_skin_offers, QUALITIES

router = Router(name="search")

@router.callback_query(F.data == "menu_search")
async def start_skin_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchSkinStates.waiting_for_name)
    await callback.message.edit_text(
        "🔍 <b>Поиск скина</b>\n\n"
        "Введите название скина (например: <code>AK-47 | Redline</code> или <code>AWP | Asiimov</code>):",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()

@router.message(SearchSkinStates.waiting_for_name)
async def process_skin_name(message: Message, state: FSMContext):
    skin_name = message.text.strip()
    if len(skin_name) < 2:
        await message.answer("⚠️ Название скина слишком короткое. Попробуйте еще раз:")
        return

    await state.update_data(skin_name=skin_name)
    await state.set_state(SearchSkinStates.waiting_for_stattrak)
    
    await message.answer(
        f"🎯 Скин: <b>{skin_name}</b>\n\n"
        "Выберите тип предмета:",
        parse_mode="HTML",
        reply_markup=get_stattrak_kb(prefix="search")
    )

@router.callback_query(SearchSkinStates.waiting_for_stattrak, F.data.startswith("search_st_"))
async def process_stattrak_choice(callback: CallbackQuery, state: FSMContext):
    is_stattrak = callback.data.endswith("_1")
    await state.update_data(is_stattrak=is_stattrak)
    await state.set_state(SearchSkinStates.waiting_for_quality)

    data = await state.get_data()
    st_prefix = "StatTrak™ " if is_stattrak else ""
    full_name = f"{st_prefix}{data['skin_name']}"

    await callback.message.edit_text(
        f"🎯 Скин: <b>{full_name}</b>\n\n"
        "Выберите качество предмета:",
        parse_mode="HTML",
        reply_markup=get_quality_kb(prefix="search")
    )
    await callback.answer()

@router.callback_query(SearchSkinStates.waiting_for_quality, F.data.startswith("search_q_"))
async def process_quality_choice(callback: CallbackQuery, state: FSMContext):
    quality_code = callback.data.split("_")[-1]
    data = await state.get_data()
    
    skin_name = data["skin_name"]
    is_stattrak = data["is_stattrak"]
    st_prefix = "StatTrak™ " if is_stattrak else ""
    quality_name = QUALITIES.get(quality_code, quality_code)
    
    # Загрузка мок-предложений
    offers = await get_mock_skin_offers(skin_name, is_stattrak, quality_code)
    
    # Сохраняем в FSM для детального просмотра
    await state.update_data(
        quality=quality_code,
        offers=[offer.__dict__ for offer in offers]
    )
    await state.set_state(SearchSkinStates.viewing_results)

    text = (
        f"📊 <b>Результаты поиска скина:</b>\n"
        f"🔫 <b>{st_prefix}{skin_name}</b>\n"
        f"⭐ Качество: <i>{quality_name}</i>\n\n"
        f"<i>Предложения отсортированы от самых дешёвых к дорогим. Нажмите на вариант для подробностей:</i>"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_offers_list_kb(offers)
    )
    await callback.answer()

@router.callback_query(SearchSkinStates.viewing_results, F.data.startswith("offer_view_"))
async def view_offer_detail(callback: CallbackQuery, state: FSMContext):
    offer_idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    offers = data.get("offers", [])
    
    if offer_idx >= len(offers):
        await callback.answer("Ошибка: предложение не найдено", show_alert=True)
        return

    offer = offers[offer_idx]
    st_prefix = "StatTrak™ " if data.get("is_stattrak") else ""
    quality_code = data.get("quality", "")
    quality_name = QUALITIES.get(quality_code, quality_code)

    lock_text = f"⏳ {offer['trade_lock_days']} дн." if offer['trade_lock_days'] > 0 else "⚡ Без задержки (Trade Ready)"
    discount_text = f"🔥 -{int(offer['discount_percent'])}%" if offer['discount_percent'] > 0 else "Нет скидки"

    detail_text = (
        f"📦 <b>Детали предложения</b>\n\n"
        f"🔫 <b>Предмет:</b> {st_prefix}{data['skin_name']}\n"
        f"⭐ <b>Качество:</b> {quality_name}\n"
        f"🏪 <b>Площадка:</b> {offer['market_name']}\n"
        f"💰 <b>Цена:</b> <code>{offer['price']:.2f} ₽</code>\n"
        f"🏷 <b>Скидка маркетплейса:</b> {discount_text}\n"
        f"⏱ <b>Trade Lock:</b> {lock_text}\n"
    )

    await callback.message.edit_text(
        text=detail_text,
        parse_mode="HTML",
        reply_markup=get_offer_detail_kb(offer["item_url"])
    )
    await callback.answer()

@router.callback_query(SearchSkinStates.viewing_results, F.data == "offer_back_list")
async def back_to_offers_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    offers_raw = data.get("offers", [])
    
    from bot.services.mock_data import MarketOffer
    offers = [MarketOffer(**o) for o in offers_raw]
    
    st_prefix = "StatTrak™ " if data.get("is_stattrak") else ""
    quality_code = data.get("quality", "")
    quality_name = QUALITIES.get(quality_code, quality_code)

    text = (
        f"📊 <b>Результаты поиска скина:</b>\n"
        f"🔫 <b>{st_prefix}{data['skin_name']}</b>\n"
        f"⭐ Качество: <i>{quality_name}</i>\n\n"
        f"<i>Предложения отсортированы от самых дешёвых к дорогим:</i>"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_offers_list_kb(offers)
    )
    await callback.answer()
