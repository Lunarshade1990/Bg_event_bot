from bot.app.handlers.imports import _format_import_summary


def test_format_import_summary_returns_simple_collection_message() -> None:
    result = {
        "bgg_username": "lunarshade",
        "collection_games_count": 15,
        "processed_games": 24,
        "created_games": 10,
        "updated_games": 7,
        "linked_games": 13,
    }

    message = _format_import_summary(result)

    assert message == "Импорт завершен для `lunarshade`.\nСейчас в твоей коллекции: 15 игр."
