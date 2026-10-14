import asyncio
import logging

from aiogram import Bot, Dispatcher

from backend.app.core.config import get_settings
from bot.app.middlewares.ephemeral_replies import (
    EphemeralReplyContextMiddleware,
    ephemeral_request_middleware,
)
from bot.app.router import router


async def main() -> None:
    settings = get_settings()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    bot = Bot(token=settings.telegram_bot_token)
    bot.session.middleware.register(ephemeral_request_middleware)
    dispatcher = Dispatcher()
    dispatcher.update.outer_middleware(EphemeralReplyContextMiddleware())
    dispatcher.include_router(router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
