import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.app.keyboards.main_menu import get_main_menu_keyboard
from bot.app.services.backend_api import BackendAPIClient
from bot.app.states.import_bgg import ImportBggStates

router = Router(name="imports")


@router.message(F.text == "Импорт из BGG")
async def start_bgg_import(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    backend_client = BackendAPIClient()

    try:
        profile = await backend_client.get_user_by_telegram_id(user.id)
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return

    if profile and profile.get("bgg_username"):
        await message.answer(
            f"Начинаю импорт коллекции для `{profile['bgg_username']}`...",
            parse_mode="Markdown",
        )
        await _run_import(
            message=message,
            backend_client=backend_client,
            telegram_id=user.id,
            bgg_username=profile["bgg_username"],
        )
        return

    await state.set_state(ImportBggStates.waiting_for_username)
    await message.answer("Пришли, пожалуйста, твой ник на BoardGameGeek.")


@router.message(ImportBggStates.waiting_for_username)
async def receive_bgg_username(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    bgg_username = (message.text or "").strip()
    if not bgg_username:
        await message.answer("Ник не должен быть пустым. Попробуй еще раз.")
        return

    backend_client = BackendAPIClient()

    try:
        await backend_client.sync_telegram_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            bgg_username=bgg_username,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось сохранить ник BGG: {_extract_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return

    await message.answer(f"Импортирую коллекцию для `{bgg_username}`...", parse_mode="Markdown")
    await _run_import(
        message=message,
        backend_client=backend_client,
        telegram_id=user.id,
        bgg_username=bgg_username,
    )
    await state.clear()


async def _run_import(
    *,
    message: Message,
    backend_client: BackendAPIClient,
    telegram_id: int,
    bgg_username: str,
) -> None:
    try:
        result = await backend_client.import_bgg_collection(
            telegram_id=telegram_id,
            bgg_username=bgg_username,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось импортировать коллекцию: {_extract_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return

    await message.answer(
        "\n".join(
            [
                f"Импорт завершен для `{result['bgg_username']}`.",
                f"Обработано игр: {result['processed_games']}",
                f"Новых карточек игр: {result['created_games']}",
                f"Обновлено карточек: {result['updated_games']}",
                f"Добавлено в твою коллекцию: {result['linked_games']}",
            ]
        ),
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


def _extract_error_detail(exc: httpx.HTTPStatusError) -> str:
    try:
        payload = exc.response.json()
    except ValueError:
        return exc.response.text
    return payload.get("detail", exc.response.text)
