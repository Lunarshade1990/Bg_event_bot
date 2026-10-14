"""Send test Rich Messages to a private Telegram chat to probe API support."""

import asyncio
import os
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import (
    FSInputFile,
    InputMediaPhoto,
    InputRichBlockCollage,
    InputRichBlockParagraph,
    InputRichBlockPhoto,
    InputRichMessage,
    RichTextBold,
)


def _photo_block(image_path: Path) -> InputRichBlockPhoto:
    return InputRichBlockPhoto(photo=InputMediaPhoto(media=FSInputFile(image_path)))


async def _main() -> None:
    token = os.environ["BOT_TOKEN"]
    chat_id = int(os.environ["TEST_CHAT_ID"])
    image_path = Path(os.environ["TEST_IMAGE"])

    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    cases = [
        (
            "collage: two photos",
            InputRichMessage(
                blocks=[
                    InputRichBlockCollage(
                        blocks=[
                            _photo_block(image_path),
                            _photo_block(image_path),
                        ]
                    )
                ]
            ),
        ),
        (
            "collage: photo + paragraph",
            InputRichMessage(
                blocks=[
                    InputRichBlockCollage(
                        blocks=[
                            _photo_block(image_path),
                            InputRichBlockParagraph(text=RichTextBold(text="Rich Message probe")),
                        ]
                    )
                ]
            ),
        ),
        (
            "top-level photo + paragraph",
            InputRichMessage(
                blocks=[
                    _photo_block(image_path),
                    InputRichBlockParagraph(text=RichTextBold(text="Rich Message probe")),
                ]
            ),
        ),
    ]

    bot = Bot(token=token)
    try:
        for name, rich_message in cases:
            try:
                sent = await bot.send_rich_message(
                    chat_id=chat_id,
                    rich_message=rich_message,
                )
            except TelegramBadRequest as exc:
                print(f"REJECTED — {name}: {exc.message}")
                continue

            print(f"ACCEPTED — {name}")
            try:
                await bot.delete_message(
                    chat_id=chat_id,
                    message_id=sent.message_id,
                )
            except TelegramAPIError as exc:
                print(f"Could not delete test message {sent.message_id}: {exc}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(_main())
