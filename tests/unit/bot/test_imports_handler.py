from types import SimpleNamespace

from bot.app.handlers.imports import _format_import_summary, receive_bgg_username


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


async def test_receive_bgg_username_clears_state_before_import(monkeypatch) -> None:
    class FakeState:
        cleared = False

        async def clear(self) -> None:
            self.cleared = True

    class FakeBackendAPIClient:
        async def sync_telegram_user(self, **kwargs) -> None:
            return None

        async def import_bgg_collection(self, **kwargs) -> dict:
            assert state.cleared
            return {
                "bgg_username": "shared_collection",
                "collection_games_count": 3,
            }

    class FakeMessage:
        from_user = SimpleNamespace(
            id=123,
            username="telegram_user",
            first_name="User",
            last_name=None,
        )
        text = "shared_collection"

        def __init__(self) -> None:
            self.answers = []

        async def answer(self, text: str, **kwargs) -> None:
            self.answers.append(text)

    state = FakeState()
    message = FakeMessage()
    monkeypatch.setattr(
        "bot.app.handlers.imports.BackendAPIClient",
        FakeBackendAPIClient,
    )

    await receive_bgg_username(message, state)

    assert state.cleared
    assert message.answers[-1].startswith("Импорт завершен")
