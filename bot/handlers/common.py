from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from bot.keyboards.main_menu import get_main_menu_kb
from bot.database.db import get_or_create_user

router = Router(name="common")

WELCOME_TEXT = (
    "<b>SkinParserBot</b>\n\n"
    "Сравнение цен и арбитраж скинов CS2 между площадками с учётом комиссий.\n\n"
    "Выберите раздел:"
)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer(
        text=WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=get_main_menu_kb()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "<b>Справка:</b>\n\n"
        "🔍 <b>Поиск скина</b> — список предложений по маркетам от самой низкой цены.\n"
        "🔄 <b>Сравнение 2 маркетов</b> — расчёт экономики круга, чистой прибыли и ROI.\n"
        "👤 <b>Профиль</b> — персональные комиссии и журнал сделок.\n\n"
        "Команда /start возвращает в главное меню."
    )
    await message.answer(help_text, parse_mode="HTML")

@router.callback_query(F.data == "menu_cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        text=WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=get_main_menu_kb()
    )
    await callback.answer()
