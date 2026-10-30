from aiogram.fsm.state import State, StatesGroup

class SearchSkinStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_stattrak = State()
    waiting_for_quality = State()
    viewing_results = State()

class CompareMarketsStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_stattrak = State()
    waiting_for_quality = State()
    waiting_for_donor = State()
    waiting_for_recipient = State()

class ProfileStates(StatesGroup):
    waiting_for_deposit_fee = State()
    waiting_for_sale_fee = State()
    waiting_for_withdraw_fee = State()
