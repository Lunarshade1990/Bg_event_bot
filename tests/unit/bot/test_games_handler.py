from bot.app.handlers.games import _format_game_line, _format_my_games_text, _parse_offset


def test_format_my_games_text_renders_page_and_game_details() -> None:
    games = [
        {
            "title": "Gloomhaven",
            "author": "Isaac Childres",
            "min_players": 1,
            "max_players": 4,
            "play_time_minutes": 180,
            "game_type": "base",
            "has_campaign": True,
        },
        {
            "title": "Codenames",
            "author": None,
            "min_players": 4,
            "max_players": 8,
            "play_time_minutes": 15,
            "game_type": "expansion",
            "has_campaign": False,
        },
    ]

    text = _format_my_games_text(games, offset=5)

    assert "<b>Мои игры</b>" in text
    assert "Страница 2" in text
    assert "6. <b>Gloomhaven</b>" in text
    assert "Автор: Isaac Childres" in text
    assert "1-4 игрок., 180 мин, База, кампания" in text
    assert "7. <b>Codenames</b>" in text
    assert "4-8 игрок., 15 мин, Дополнение" in text


def test_format_game_line_escapes_html_in_game_fields() -> None:
    text = _format_game_line(
        index=1,
        game={
            "title": "<Root>",
            "author": "Tom & Jerry",
            "min_players": 2,
            "max_players": 2,
            "play_time_minutes": None,
            "game_type": "base",
            "has_campaign": False,
        },
    )

    assert "&lt;Root&gt;" in text
    assert "Tom &amp; Jerry" in text
    assert "2 игрок." in text
    assert "время не указано" in text


def test_parse_offset_returns_none_for_invalid_callback_data() -> None:
    assert _parse_offset("my_games:10") == 10
    assert _parse_offset("my_games:not-a-number") is None
    assert _parse_offset("other:10") is None
    assert _parse_offset(None) is None
