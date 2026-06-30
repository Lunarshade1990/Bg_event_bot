from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мои игры"), KeyboardButton(text="Игры других")],
            [KeyboardButton(text="Импорт из BGG"), KeyboardButton(text="Встречи")],
            [KeyboardButton(text="Профиль")],
        ],
        resize_keyboard=True,
    )
