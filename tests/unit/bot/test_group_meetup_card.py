from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.types import (
    BufferedInputFile,
    InputRichBlockButtons,
    InputRichBlockParagraph,
    InputRichBlockPhoto,
    InputRichBlockSlideshow,
)

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
async def test_group_meetup_rich_card_places_cover_slideshow_at_the_beginning(
    monkeypatch,
) -> None:
    photos: list[BufferedInputFile | None] = [
        BufferedInputFile(b"first-cover", filename="first.jpg"),
        None,
        BufferedInputFile(b"second-cover", filename="second.jpg"),
    ]

    async def load_photos(games: list[dict]) -> list[BufferedInputFile | None]:
        assert len(games) == 3
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
                {"title": "Wingspan", "image_url": "https://example.test/wingspan.jpg"},
            ],
        }
    )

    blocks = rich_message.blocks or []
    game_title_positions = [
        index
        for index, block in enumerate(blocks)
        if isinstance(block, InputRichBlockParagraph)
        and getattr(block.text, "text", None) in {"Catan", "Carcassonne", "Wingspan"}
    ]
    slideshow_positions = [
        index for index, block in enumerate(blocks) if isinstance(block, InputRichBlockSlideshow)
    ]

    assert [
        getattr(getattr(blocks[index], "text", None), "text", None)
        for index in game_title_positions
    ] == ["Catan", "Carcassonne", "Wingspan"]
    assert len(slideshow_positions) == 1
    assert slideshow_positions[0] == 0
    slideshow = blocks[slideshow_positions[0]]
    assert isinstance(slideshow, InputRichBlockSlideshow)
    assert sum(isinstance(block, InputRichBlockPhoto) for block in slideshow.blocks) == 2


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
    assert not any(isinstance(block, InputRichBlockSlideshow) for block in blocks)


@pytest.mark.asyncio
async def test_group_meetup_rich_card_adds_one_vote_button_per_game_and_shows_voters(
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
            "id": 42,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "participants": [],
            "game_suggestions": [
                {
                    "username": "alice",
                    "display_name": "Alice",
                    "games": [{"id": 7, "title": "Catan"}],
                },
                {
                    "username": None,
                    "display_name": "Bob",
                    "games": [{"id": 7, "title": "Catan"}],
                },
            ],
            "game_suggestion_votes": [
                {
                    "game_id": 7,
                    "voters": [
                        {"user_id": 1, "username": "alice", "display_name": "Alice"},
                        {"user_id": 2, "username": None, "display_name": "Bob"},
                    ],
                }
            ],
        }
    )

    blocks = rich_message.blocks or []
    buttons = [
        button
        for block in blocks
        if isinstance(block, InputRichBlockButtons)
        for button in block.buttons
    ]
    assert len(buttons) == 1
    assert buttons[0].text == "Catan"
    assert buttons[0].callback_data == "meetup_game_vote:42:7"
    assert any(
        isinstance(block, InputRichBlockParagraph) and block.text == "✅ За: @alice, Bob"
        for block in blocks
    )


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
