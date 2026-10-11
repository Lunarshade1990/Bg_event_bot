from aiogram.fsm.state import State, StatesGroup


class ProposeMeetupGameStates(StatesGroup):
    choosing_source = State()
    choosing_collection_owner = State()
    choosing_game_group = State()
    choosing_game_letter = State()
    choosing_games = State()
