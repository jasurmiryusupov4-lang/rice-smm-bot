from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    selecting_category = State()
    selecting_service = State()
    entering_link = State()
    entering_quantity = State()
    confirming_order = State()

class PaymentStates(StatesGroup):
    entering_amount = State()
    waiting_receipt = State()

class AdminStates(StatesGroup):
    broadcasting = State()
    adjust_balance_user_id = State()
    adjust_balance_amount = State()
    change_price_id = State()
    change_price_val = State()
