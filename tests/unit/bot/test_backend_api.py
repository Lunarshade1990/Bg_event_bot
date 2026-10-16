from types import SimpleNamespace

import pytest

from bot.app.services import backend_api


@pytest.mark.parametrize(
    ("bgg_username", "includes_bgg_username"),
    [(None, False), ("shared_bgg", True)],
)
async def test_sync_telegram_user_only_sends_bgg_username_when_provided(
    monkeypatch: pytest.MonkeyPatch,
    bgg_username: str | None,
    includes_bgg_username: bool,
) -> None:
    captured_payloads: list[dict] = []

    class FakeHTTPClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, *, json: dict) -> SimpleNamespace:
            captured_payloads.append(json)
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {})

    monkeypatch.setattr(backend_api.httpx, "AsyncClient", FakeHTTPClient)
    client = backend_api.BackendAPIClient.__new__(backend_api.BackendAPIClient)
    client._base_url = "http://backend"
    client._headers = {}

    await client.sync_telegram_user(
        telegram_id=123,
        username="telegram",
        first_name="Player",
        last_name=None,
        bgg_username=bgg_username,
    )

    assert ("bgg_username" in captured_payloads[0]) is includes_bgg_username


async def test_update_meetup_sends_only_changed_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_request: dict = {}

    class FakeHTTPClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def patch(self, url: str, *, json: dict) -> SimpleNamespace:
            captured_request.update(url=url, payload=json)
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"id": 42})

    monkeypatch.setattr(backend_api.httpx, "AsyncClient", FakeHTTPClient)
    client = backend_api.BackendAPIClient.__new__(backend_api.BackendAPIClient)
    client._base_url = "http://backend"
    client._headers = {}

    response = await client.update_meetup(
        42,
        requesting_user_id=7,
        fields={"title": None},
    )

    assert response == {"id": 42}
    assert captured_request == {
        "url": "/api/meetups/42",
        "payload": {"requesting_user_id": 7, "title": None},
    }
