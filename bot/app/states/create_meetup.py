from aiogram.fsm.state import State, StatesGroup


class CreateMeetupStates(StatesGroup):
    waiting_for_chat_selection = State()
    waiting_for_game_group = State()
    waiting_for_game_letter = State()
    waiting_for_game_selection = State()
    waiting_for_date = State()
    waiting_for_capacity = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()
