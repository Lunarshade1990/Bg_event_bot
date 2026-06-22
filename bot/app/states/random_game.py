from aiogram.fsm.state import State, StatesGroup


class RandomGameState(StatesGroup):
    waiting_for_players_count = State()