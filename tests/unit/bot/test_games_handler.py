from bot.app.handlers.games import (
    _build_grouped_entry,
    _format_grouped_game_line,
    _format_my_games_text,
    _group_owned_games,
    _parse_offset,
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


def test_format_my_games_text_renders_expansions_line() -> None:
    entries = [
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
    ]

    text = _format_my_games_text(entries, offset=5)

    assert "<b>Мои игры</b>" in text
    assert "Страница 2" in text
    assert "6. <b>Gloomhaven</b>" in text
    assert "Автор: Isaac Childres" in text
    assert "1-6 игрок., 180 мин, База, кампания" in text
    assert "Допы: Forgotten Circles, Jaws Crossover" in text


def test_format_grouped_game_line_escapes_html_in_game_fields() -> None:
    text = _format_grouped_game_line(
        index=1,
        entry={
            "game": {
                "title": "<Root>",
                "author": "Tom & Jerry",
                "play_time_minutes": None,
                "game_type": "base",
                "has_campaign": False,
            },
            "expansions": [{"title": "<Riverfolk>"}],
            "display_min_players": 2,
            "display_max_players": 2,
        },
    )

    assert "&lt;Root&gt;" in text
    assert "Tom &amp; Jerry" in text
    assert "2 игрок." in text
    assert "время не указано" in text
    assert "&lt;Riverfolk&gt;" in text


def test_parse_offset_returns_none_for_invalid_callback_data() -> None:
    assert _parse_offset("my_games:10") == 10
    assert _parse_offset("my_games:not-a-number") is None
    assert _parse_offset("other:10") is None
    assert _parse_offset(None) is None
