from aiogram.fsm.state import State, StatesGroup


class RandomGameState(StatesGroup):
    waiting_for_players_count = State()


class RandomizerStates(StatesGroup):
    waiting_for_game_query = State()
    waiting_for_category_name = State()
    waiting_for_category_count = State()
    waiting_for_category_rename = State()
    waiting_for_category_count_update = State()
    waiting_for_options = State()
    waiting_for_option_update = State()
    waiting_for_draw_players_count = State()
