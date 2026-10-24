from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

COLLECTIONS_MENU_TEXT = "Коллекции игр"
RANDOMIZERS_MENU_TEXT = "Рандомайзеры"
IMPORT_MENU_TEXT = "Импорт из BGG"
MEETUPS_MENU_TEXT = "Сборы на настолки"
MY_GAMES_BUTTON_TEXT = "Мои игры"
OTHER_GAMES_BUTTON_TEXT = "Игры других"
RANDOM_GAME_BUTTON_TEXT = "Игры"
RANDOMIZER_COMPONENTS_BUTTON_TEXT = "Компоненты"
BACK_BUTTON_TEXT = "Назад"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=COLLECTIONS_MENU_TEXT)],
            [KeyboardButton(text=RANDOMIZERS_MENU_TEXT)],
            [KeyboardButton(text=IMPORT_MENU_TEXT)],
            [KeyboardButton(text=MEETUPS_MENU_TEXT)],
        ],
        resize_keyboard=True,
    )


def get_collections_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=MY_GAMES_BUTTON_TEXT),
                KeyboardButton(text=OTHER_GAMES_BUTTON_TEXT),
            ],
            [KeyboardButton(text=BACK_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )


def get_randomizers_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=RANDOM_GAME_BUTTON_TEXT),
                KeyboardButton(text=RANDOMIZER_COMPONENTS_BUTTON_TEXT),
            ],
            [KeyboardButton(text=BACK_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )
