from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.app.handlers.games import open_collections_menu
from bot.app.handlers.random_game import get_random_game_from_user_list
from bot.app.handlers.randomizer import open_randomizers_menu
from bot.app.keyboards.main_menu import (
    BACK_BUTTON_TEXT,
    COLLECTIONS_MENU_TEXT,
    IMPORT_MENU_TEXT,
    MEETUPS_MENU_TEXT,
    MY_GAMES_BUTTON_TEXT,
    OTHER_GAMES_BUTTON_TEXT,
    RANDOM_GAME_BUTTON_TEXT,
    RANDOMIZER_COMPONENTS_BUTTON_TEXT,
    RANDOMIZERS_MENU_TEXT,
    get_collections_menu_keyboard,
    get_main_menu_keyboard,
    get_randomizers_menu_keyboard,
)
from bot.app.states.random_game import RandomGameState


def _labels(keyboard) -> list[list[str]]:
    return [[button.text for button in row] for row in keyboard.keyboard]


def test_main_menu_keyboard_layout() -> None:
    assert _labels(get_main_menu_keyboard()) == [
        [COLLECTIONS_MENU_TEXT],
        [RANDOMIZERS_MENU_TEXT],
        [IMPORT_MENU_TEXT],
        [MEETUPS_MENU_TEXT],
    ]


def test_collections_menu_keyboard_layout() -> None:
    assert _labels(get_collections_menu_keyboard()) == [
        [MY_GAMES_BUTTON_TEXT, OTHER_GAMES_BUTTON_TEXT],
        [BACK_BUTTON_TEXT],
    ]


def test_randomizers_menu_keyboard_layout() -> None:
    assert _labels(get_randomizers_menu_keyboard()) == [
        [RANDOM_GAME_BUTTON_TEXT, RANDOMIZER_COMPONENTS_BUTTON_TEXT],
        [BACK_BUTTON_TEXT],
    ]


async def test_open_collections_menu_shows_submenu() -> None:
    message = SimpleNamespace(answer=AsyncMock())

    await open_collections_menu(message)

    message.answer.assert_awaited_once()
    kwargs = message.answer.await_args.kwargs
    assert message.answer.await_args.args[0] == "Коллекции игр:"
    assert _labels(kwargs["reply_markup"]) == _labels(get_collections_menu_keyboard())


async def test_open_randomizers_menu_clears_state_and_shows_submenu() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    state = SimpleNamespace(clear=AsyncMock())

    await open_randomizers_menu(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    kwargs = message.answer.await_args.kwargs
    assert message.answer.await_args.args[0] == "Рандомайзеры:"
    assert _labels(kwargs["reply_markup"]) == _labels(get_randomizers_menu_keyboard())


async def test_random_game_button_starts_player_count_prompt() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    state = SimpleNamespace(set_state=AsyncMock())

    await get_random_game_from_user_list(message, state)

    state.set_state.assert_awaited_once_with(RandomGameState.waiting_for_players_count)
    message.answer.assert_awaited_once_with("Сколько человек будет играть?")
