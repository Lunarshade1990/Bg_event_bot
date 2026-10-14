import asyncio
import logging
from io import BytesIO

import httpx
from aiogram.types import BufferedInputFile
from PIL import Image

logger = logging.getLogger(__name__)

MAX_COVER_BYTES = 5 * 1024 * 1024
MAX_COVER_PIXELS = 20_000_000
COVER_SIZE = (240, 360)


async def load_game_cover_photos(games: list[dict]) -> list[BufferedInputFile | None]:
    if not games:
        return []

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(5)

        async def load_photo(index: int, game: dict) -> BufferedInputFile | None:
            async with semaphore:
                return await _load_game_cover_photo(client, game, index)

        photos = await asyncio.gather(
            *(load_photo(index, game) for index, game in enumerate(games, start=1))
        )
        return list(photos)


async def _load_game_cover_photo(
    client: httpx.AsyncClient,
    game: dict,
    index: int,
) -> BufferedInputFile | None:
    image_url = game.get("image_url")
    if not isinstance(image_url, str) or not image_url:
        return None

    try:
        async with client.stream("GET", image_url) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length is not None and int(content_length) > MAX_COVER_BYTES:
                raise ValueError("image exceeds the size limit")

            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_COVER_BYTES:
                    raise ValueError("image exceeds the size limit")

        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > MAX_COVER_PIXELS:
                raise ValueError("image exceeds the pixel limit")
            image.thumbnail(COVER_SIZE, Image.Resampling.LANCZOS)
            image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="JPEG", quality=85)
    except (
        httpx.HTTPError,
        httpx.InvalidURL,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        logger.warning(
            "Skipping unavailable game cover at list position %s (%s)",
            index,
            type(exc).__name__,
        )
        return None

    return BufferedInputFile(output.getvalue(), filename=f"game-cover-{index}.jpg")
