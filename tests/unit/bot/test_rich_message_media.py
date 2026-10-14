from io import BytesIO

import httpx
import pytest
from aiogram.types import BufferedInputFile
from PIL import Image

from bot.app.services.rich_message_media import _load_game_cover_photo


@pytest.mark.asyncio
async def test_load_game_cover_photo_normalizes_valid_image() -> None:
    image_content = BytesIO()
    Image.new("RGB", (1200, 800), "white").save(image_content, format="PNG")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=image_content.getvalue()))

    async with httpx.AsyncClient(transport=transport) as client:
        photo = await _load_game_cover_photo(
            client,
            {"image_url": "https://example.test/cover.png"},
            1,
        )

    assert isinstance(photo, BufferedInputFile)
    assert photo.filename == "game-cover-1.jpg"
    with Image.open(BytesIO(photo.data)) as thumbnail:
        assert thumbnail.size == (240, 160)


@pytest.mark.asyncio
async def test_load_game_cover_photo_omits_unavailable_image() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(404))

    async with httpx.AsyncClient(transport=transport) as client:
        photo = await _load_game_cover_photo(
            client,
            {"image_url": "https://example.test/missing.jpg"},
            1,
        )

    assert photo is None


@pytest.mark.asyncio
async def test_load_game_cover_photo_skips_invalid_image_data() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b"not an image"))

    async with httpx.AsyncClient(transport=transport) as client:
        photo = await _load_game_cover_photo(
            client,
            {"image_url": "https://example.test/invalid.jpg"},
            1,
        )

    assert photo is None
