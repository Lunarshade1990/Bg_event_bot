from backend.app.db import models  # noqa: F401
from backend.app.db.base import Base


def test_all_expected_tables_are_registered() -> None:
    expected_tables = {
        "bgg_import_jobs",
        "games",
        "game_randomizer_categories",
        "game_randomizer_options",
        "meetup_games",
        "meetup_participants",
        "meetups",
        "user_games",
        "users",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())
