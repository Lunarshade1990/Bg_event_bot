from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from aiogram.types import (
    BufferedInputFile,
    InputRichBlockParagraph,
    InputRichBlockPhoto,
    InputRichBlockSlideshow,
    InputRichMessage,
    Message,
)

from bot.app.handlers.games import (
    _build_games_rich_message,
    _format_user_display_name,
    _parse_other_games_callback,
    _parse_single_offset,
    _send_games_rich_message,
)
from bot.app.services.game_service import (
    _build_grouped_entry,
    _group_owned_games,
)
from bot.app.utils.game_player_counts import (
    calculate_game_max_players_with_expansions,
    calculate_max_for_all_selected_games,
)


def test_group_owned_games_attaches_single_owned_base_expansions() -> None:
    games = [
        {
            "id": 1,
            "bgg_id": 100,
            "title": "Base Game",
            "author": "Author",
            "min_players": 1,
            "max_players": 4,
            "play_time_minutes": 90,
            "game_type": "base",
            "has_campaign": False,
            "bgg_expands_ids_cached": [],
        },
        {
            "id": 2,
            "bgg_id": 101,
            "title": "Extra Players",
            "author": None,
            "min_players": 1,
            "max_players": 5,
            "play_time_minutes": 30,
            "game_type": "expansion",
            "has_campaign": False,
            "bgg_expands_ids_cached": [100],
        },
        {
            "id": 3,
            "bgg_id": 102,
            "title": "Standalone Expansion",
            "author": None,
            "min_players": 1,
            "max_players": 6,
            "play_time_minutes": 45,
            "game_type": "expansion",
            "has_campaign": False,
            "bgg_expands_ids_cached": [],
        },
    ]

    grouped = _group_owned_games(games)

    assert len(grouped) == 2
    assert grouped[0]["game"]["title"] == "Base Game"
    assert [exp["title"] for exp in grouped[0]["expansions"]] == ["Extra Players"]
    assert grouped[1]["game"]["title"] == "Standalone Expansion"


def test_group_owned_games_attaches_multi_parent_expansion_to_all_matched_bases() -> None:
    games = [
        {
            "id": 1,
            "bgg_id": 100,
            "title": "Black Rose Wars",
            "author": "Author",
            "min_players": 1,
            "max_players": 4,
            "play_time_minutes": 90,
            "game_type": "base",
            "has_campaign": False,
            "bgg_expands_ids_cached": [],
        },
        {
            "id": 2,
            "bgg_id": 200,
            "title": "Black Rose Wars: Rebirth",
            "author": "Author",
            "min_players": 1,
            "max_players": 4,
            "play_time_minutes": 90,
            "game_type": "base",
            "has_campaign": False,
            "bgg_expands_ids_cached": [],
        },
        {
            "id": 3,
            "bgg_id": 300,
            "title": "Black Rose Wars: Sator Box",
            "author": "Author",
            "min_players": 1,
            "max_players": 6,
            "play_time_minutes": 180,
            "game_type": "expansion",
            "has_campaign": False,
            "bgg_expands_ids_cached": [100, 200],
        },
    ]

    grouped = _group_owned_games(games)

    assert len(grouped) == 2
    assert grouped[0]["game"]["title"] == "Black Rose Wars"
    assert [exp["title"] for exp in grouped[0]["expansions"]] == [
        "Black Rose Wars: Sator Box"
    ]
    assert grouped[1]["game"]["title"] == "Black Rose Wars: Rebirth"
    assert [exp["title"] for exp in grouped[1]["expansions"]] == [
        "Black Rose Wars: Sator Box"
    ]


def test_build_grouped_entry_sums_extra_players_from_multiple_expansions() -> None:
    base_game = {
        "title": "Base Game",
        "min_players": 1,
        "max_players": 4,
        "game_type": "base",
    }
    expansions = [
        {"title": "Expansion One", "max_players": 5},
        {"title": "Expansion Two", "max_players": 5},
    ]

    entry = _build_grouped_entry(base_game, expansions)

    assert entry["display_min_players"] == 1
    assert entry["display_max_players"] == 6


def test_calculate_game_max_players_with_expansions_counts_extra_players() -> None:
    base_game = {"max_players": 4, "game_type": "base"}
    expansions = [
        {"max_players": 5},
        {"max_players": 5},
    ]

    assert calculate_game_max_players_with_expansions(base_game, expansions) == 6


def test_calculate_game_max_players_with_expansions_returns_base_max_when_no_expansions() -> None:
    base_game = {"max_players": 4, "game_type": "base"}
    assert calculate_game_max_players_with_expansions(base_game, []) == 4


def test_calculate_max_for_all_selected_games_considers_owned_expansions() -> None:
    selected_games = [
        {"bgg_id": 100, "max_players": 4, "game_type": "base"},
        {"bgg_id": 200, "max_players": 5, "game_type": "base"},
    ]
    owned_expansions = [
        {"max_players": 5, "bgg_expands_ids_cached": [100]},
        {"max_players": 6, "bgg_expands_ids_cached": [100]},
    ]

    assert calculate_max_for_all_selected_games(selected_games, owned_expansions) == 5


def test_parse_offset_returns_none_for_invalid_callback_data() -> None:
    assert _parse_single_offset("my_games:10", "my_games") == 10
    assert _parse_single_offset("my_games:not-a-number", "my_games") is None
    assert _parse_single_offset("other:10", "my_games") is None
    assert _parse_single_offset(None, "my_games") is None


def test_format_user_display_name_prefers_username() -> None:
    assert _format_user_display_name({"username": "alice", "display_name": "Alice"}) == "@alice"
    assert _format_user_display_name({"username": None, "display_name": "Bob"}) == "Bob"


def test_parse_other_games_callback() -> None:
    assert _parse_other_games_callback("other_games:12:0") == (12, 0)
    assert _parse_other_games_callback("other_games:12:bad") is None


def test_games_rich_message_groups_covers_in_slideshow_after_game_entries() -> None:
    entries = [
        {
            "game": {"title": "Catan"},
            "expansions": [],
            "display_min_players": 2,
            "display_max_players": 4,
        },
        {
            "game": {"title": "Carcassonne"},
            "expansions": [],
            "display_min_players": 2,
            "display_max_players": 5,
        },
        {
            "game": {"title": "Wingspan"},
            "expansions": [],
            "display_min_players": 1,
            "display_max_players": 5,
        },
    ]
    rich_message = _build_games_rich_message(
        title="Мои игры",
        entries=entries,
        offset=0,
        game_photos=[
            BufferedInputFile(b"first-cover", filename="first.jpg"),
            None,
            BufferedInputFile(b"second-cover", filename="second.jpg"),
        ],
    )

    blocks = rich_message.blocks or []
    title_positions = [
        index
        for index, block in enumerate(blocks)
        if isinstance(block, InputRichBlockParagraph)
        and getattr(block.text, "text", None) in {"1. Catan", "2. Carcassonne", "3. Wingspan"}
    ]
    slideshow_positions = [
        index for index, block in enumerate(blocks) if isinstance(block, InputRichBlockSlideshow)
    ]

    assert [
        getattr(getattr(blocks[index], "text", None), "text", None) for index in title_positions
    ] == [
        "1. Catan",
        "2. Carcassonne",
        "3. Wingspan",
    ]
    assert len(slideshow_positions) == 1
    assert slideshow_positions[0] == len(blocks) - 1
    slideshow = blocks[slideshow_positions[0]]
    assert isinstance(slideshow, InputRichBlockSlideshow)
    assert sum(isinstance(block, InputRichBlockPhoto) for block in slideshow.blocks) == 2


def test_games_rich_message_keeps_game_details_and_expansions() -> None:
    rich_message = _build_games_rich_message(
        title="Мои игры",
        entries=[
            {
                "game": {
                    "title": "Gloomhaven",
                    "author": "Isaac Childres",
                    "play_time_minutes": 180,
                    "game_type": "base",
                    "has_campaign": True,
                },
                "expansions": [
                    {"title": "Forgotten Circles"},
                    {"title": "Jaws Crossover"},
                ],
                "display_min_players": 1,
                "display_max_players": 6,
            }
        ],
        offset=5,
        game_photos=[None],
    )

    paragraphs = "\n".join(
        block.text if isinstance(block.text, str) else getattr(block.text, "text", "")
        for block in rich_message.blocks or []
        if isinstance(block, InputRichBlockParagraph)
    )

    assert "Страница 2" in paragraphs
    assert "Автор: Isaac Childres" in paragraphs
    assert "1-6 игрок., 180 мин, База, кампания" in paragraphs
    assert "Допы: Forgotten Circles, Jaws Crossover" in paragraphs


def test_games_rich_message_keeps_entries_without_cover_photos() -> None:
    rich_message = _build_games_rich_message(
        title="Мои игры",
        entries=[
            {
                "game": {"title": "Catan"},
                "expansions": [],
                "display_min_players": 2,
                "display_max_players": 4,
            }
        ],
        offset=0,
        game_photos=[None],
    )

    blocks = rich_message.blocks or []
    paragraphs = [block.text for block in blocks if isinstance(block, InputRichBlockParagraph)]
    assert any(getattr(paragraph, "text", None) == "1. Catan" for paragraph in paragraphs)
    assert not any(isinstance(block, InputRichBlockSlideshow) for block in blocks)


@pytest.mark.asyncio
async def test_send_games_rich_message_edits_existing_page_as_rich_message() -> None:
    edit_text = AsyncMock()
    message = cast(Message, SimpleNamespace(edit_text=edit_text))
    rich_message = InputRichMessage(html="My games")

    await _send_games_rich_message(
        message=message,
        rich_message=rich_message,
        edit_message=True,
    )

    edit_text.assert_awaited_once_with(
        rich_message=rich_message,
        reply_markup=None,
    )
