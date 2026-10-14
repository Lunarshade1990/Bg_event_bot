from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.types import BufferedInputFile, InputRichBlockParagraph, InputRichBlockPhoto

from bot.app.handlers.meetups import (
    _build_group_meetup_rich_message,
    _format_group_meetup_card,
    _refresh_group_meetup_card,
)


def test_group_meetup_card_does_not_contain_ids() -> None:
    text = _format_group_meetup_card(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": "Test",
            "participants": [
                {
                    "telegram_id": 100,
                    "display_name": "Anna",
                    "username": "anna_test",
                    "status": "joined",
                }
            ],
        }
    )

    assert "100" not in text
    assert "@anna_test" in text


@pytest.mark.asyncio
async def test_group_meetup_rich_card_interleaves_game_titles_and_cover_photos(
    monkeypatch,
) -> None:
    photos: list[BufferedInputFile | None] = [
        BufferedInputFile(b"first-cover", filename="first.jpg"),
        BufferedInputFile(b"second-cover", filename="second.jpg"),
    ]

    async def load_photos(games: list[dict]) -> list[BufferedInputFile | None]:
        assert len(games) == 2
        return photos

    monkeypatch.setattr(
        "bot.app.handlers.meetups.load_game_cover_photos",
        load_photos,
    )

    rich_message = await _build_group_meetup_rich_message(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "participants": [],
            "games": [
                {"title": "Catan", "image_url": "https://example.test/catan.jpg"},
                {"title": "Carcassonne", "image_url": "https://example.test/carcassonne.jpg"},
            ],
        }
    )

    blocks = rich_message.blocks or []
    game_title_positions = [
        index
        for index, block in enumerate(blocks)
        if isinstance(block, InputRichBlockParagraph)
        and getattr(block.text, "text", None) in {"Catan", "Carcassonne"}
    ]
    photo_positions = [
        index for index, block in enumerate(blocks) if isinstance(block, InputRichBlockPhoto)
    ]

    assert [
        getattr(getattr(blocks[index], "text", None), "text", None)
        for index in game_title_positions
    ] == ["Catan", "Carcassonne"]
    assert photo_positions == [game_title_positions[0] + 1, game_title_positions[1] + 1]


@pytest.mark.asyncio
async def test_group_meetup_rich_card_keeps_game_title_when_cover_missing(
    monkeypatch,
) -> None:
    async def load_photos(games: list[dict]) -> list[None]:
        return [None for _ in games]

    monkeypatch.setattr(
        "bot.app.handlers.meetups.load_game_cover_photos",
        load_photos,
    )

    rich_message = await _build_group_meetup_rich_message(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "participants": [],
            "games": [{"title": "Catan", "image_url": None}],
        }
    )

    blocks = rich_message.blocks or []
    assert any(
        isinstance(block, InputRichBlockParagraph) and getattr(block.text, "text", None) == "Catan"
        for block in blocks
    )
    assert not any(isinstance(block, InputRichBlockPhoto) for block in blocks)


@pytest.mark.asyncio
async def test_refresh_group_meetup_card_edits_message_as_rich_message(monkeypatch) -> None:
    async def load_photos(games: list[dict]) -> list[None]:
        return [None for _ in games]

    monkeypatch.setattr(
        "bot.app.handlers.meetups.load_game_cover_photos",
        load_photos,
    )
    edit_message_text = AsyncMock()
    bot = cast(Bot, SimpleNamespace(edit_message_text=edit_message_text))

    await _refresh_group_meetup_card(
        bot,
        {
            "id": 42,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "telegram_chat_id": -1001,
            "telegram_message_id": 123,
            "participants": [],
            "games": [{"title": "Catan", "image_url": None}],
        },
        telegram_id=100,
        has_photo=False,
    )

    edit_message_text.assert_awaited_once()
    request = edit_message_text.await_args.kwargs
    assert request["chat_id"] == -1001
    assert request["message_id"] == 123
    assert request["rich_message"].blocks
