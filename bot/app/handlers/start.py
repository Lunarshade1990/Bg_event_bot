import httpx
from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.app.handlers.meetups import start_suggestion_from_deep_link
from bot.app.keyboards.main_menu import get_main_menu_keyboard
from bot.app.services.backend_api import BackendAPIClient

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject) -> None:
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

    args = command.args or ""
    parts = args.split("_")
    if (
        len(parts) == 3
        and parts[0] == "suggest"
        and parts[1].isdigit()
        and parts[2] in {"0", "1"}
    ):
        await start_suggestion_from_deep_link(
            message,
            state,
            meetup_id=int(parts[1]),
            card_has_photo=parts[2] == "1",
        )
        return

    await message.answer(
        "Привет! Я помогу организовывать встречи на настольные игры.",
        reply_markup=get_main_menu_keyboard(),
    )
