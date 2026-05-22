import httpx
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.app.keyboards.main_menu import get_main_menu_keyboard
from bot.app.services.backend_api import BackendAPIClient

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    backend_client = BackendAPIClient()
    user = message.from_user

    if user is not None:
        try:
            await backend_client.sync_telegram_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
        except httpx.HTTPError:
            await message.answer(
                "Backend сейчас недоступен, но бот уже запущен. Попробуй еще раз чуть позже.",
            )
            return

    await message.answer(
        "Привет! Я помогу организовывать встречи на настольные игры.",
        reply_markup=get_main_menu_keyboard(),
    )
