from aiogram.fsm.state import State, StatesGroup


class ImportBggStates(StatesGroup):
    waiting_for_username = State()
