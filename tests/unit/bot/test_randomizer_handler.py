from bot.app.handlers.randomizer import (
    _category_details_keyboard,
    _format_draw_result,
    _parse_draw_count,
)
from bot.app.keyboards.meetups import get_games_list_keyboard


def test_parse_draw_count_supports_fixed_and_player_based_counts() -> None:
    assert _parse_draw_count("3") == 3
    assert _parse_draw_count("по числу игроков") is None
    assert _parse_draw_count("0") is False
    assert _parse_draw_count("много") is False


def test_format_draw_result_reports_shortage_without_partial_values() -> None:
    text = _format_draw_result(
        {
            "game": {"title": "Test Game"},
            "categories": [
                {
                    "category_name": "Нации",
                    "requested_count": 3,
                    "available_count": 1,
                    "shortage": 2,
                    "selected": [],
                }
            ],
        }
    )

    assert "Не хватает вариантов: нужно 3, есть 1." in text


def test_category_options_are_paginated_for_editing() -> None:
    category = {
        "id": 2,
        "name": "Духи",
        "draw_count": None,
        "options": [{"id": index, "value": f"Дух {index}"} for index in range(1, 26)],
    }

    keyboard, text = _category_details_keyboard(1, category, offset=20)

    option_buttons = [
        row[0] for row in keyboard.inline_keyboard if row[0].callback_data.startswith("rz:option:")
    ]
    assert len(option_buttons) == 5
    assert option_buttons[0].callback_data == "rz:option:1:2:21:20"
    assert "Страница 2 из 2." in text


def test_randomizer_game_picker_uses_single_select_meetup_keyboard() -> None:
    keyboard = get_games_list_keyboard(
        [{"id": 42, "title": "Spirit Island"}],
        set(),
        page=0,
        has_more=False,
        callback_prefix="rz:pickgame",
        page_callback_prefix="rz:gamepage",
        show_selection=False,
        include_done=False,
        include_skip=False,
        back_callback_data="rz:picker:back",
    )

    assert keyboard.inline_keyboard[0][0].text == "Spirit Island"
    assert keyboard.inline_keyboard[0][0].callback_data == "rz:pickgame:42"
    assert keyboard.inline_keyboard[-1][0].callback_data == "rz:picker:back"
    assert all(
        button.text not in {"Done", "Skip"} for row in keyboard.inline_keyboard for button in row
    )
