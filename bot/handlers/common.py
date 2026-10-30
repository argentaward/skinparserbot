from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from bot.keyboards.main_menu import get_main_menu_kb
from bot.database.db import get_or_create_user

router = Router(name="common")

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в SkinParserBot!</b>\n\n"
    "Этот бот помогает находить выгодные скины CS2 и сравнивать цены между площадками "
    "с полным учётом всех комиссий (ввод, продажа, вывод).\n\n"
    "Выберите нужное действие ниже:"
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
        "📖 <b>Справка по боту:</b>\n\n"
        "🔍 <b>Поиск скина</b> — введите скин, выберите качество и StatTrak. Бот покажет все маркеты, отсортированные от самой низкой цены к высокой.\n"
        "🔄 <b>Сравнение 2 маркетов</b> — выберите донора и реципиента для подсчёта чистой прибыли круга и ROI.\n"
        "👤 <b>Профиль</b> — настройте ваши личные комиссии платежных систем и просматривайте журнал закрытых сделок.\n\n"
        "Команда /start вернёт вас в главное меню в любой момент."
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
