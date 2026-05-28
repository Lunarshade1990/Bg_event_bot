from aiogram.fsm.state import State, StatesGroup


class CreateMeetupStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_capacity = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()
