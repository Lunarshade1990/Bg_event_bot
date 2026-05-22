from html import escape

import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.app.keyboards.games import (
    MY_GAMES_CALLBACK_PREFIX,
    MY_GAMES_PAGE_SIZE,
    get_my_games_keyboard,
)
from bot.app.services.backend_api import BackendAPIClient

router = Router(name="games")


@router.message(F.text == "Мои игры")
async def show_my_games(message: Message) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    await _render_my_games_page(message=message, telegram_id=user.id, offset=0)


@router.callback_query(F.data.startswith(f"{MY_GAMES_CALLBACK_PREFIX}:"))
async def paginate_my_games(callback: CallbackQuery) -> None:
    user = callback.from_user
    message = callback.message

    if message is None:
        await callback.answer("Не удалось обновить список игр.", show_alert=True)
        return

    offset = _parse_offset(callback.data)
    if offset is None:
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    page_rendered = await _render_my_games_page(
        message=message,
        telegram_id=user.id,
        offset=offset,
        edit_message=True,
    )

    if not page_rendered:
        previous_offset = max(offset - MY_GAMES_PAGE_SIZE, 0)
        if previous_offset != offset:
            await callback.answer("Список игр изменился, показываю предыдущую страницу.")
            await _render_my_games_page(
                message=message,
                telegram_id=user.id,
                offset=previous_offset,
                edit_message=True,
            )
            return

    await callback.answer()


async def _render_my_games_page(
    *,
    message: Message,
    telegram_id: int,
    offset: int,
    edit_message: bool = False,
) -> bool:
    backend_client = BackendAPIClient()

    try:
        profile = await backend_client.get_user_by_telegram_id(telegram_id)
    except httpx.HTTPError:
        await _send_games_message(
            message=message,
            text="Не удалось связаться с backend API.",
            edit_message=edit_message,
        )
        return True

    if profile is None:
        await _send_games_message(
            message=message,
            text="Я не нашел твой профиль. Нажми /start, чтобы синхронизироваться с backend.",
            edit_message=edit_message,
        )
        return True

    try:
        games = await backend_client.list_games(
            owner_id=profile["id"],
            limit=MY_GAMES_PAGE_SIZE + 1,
            offset=offset,
        )
    except httpx.HTTPError:
        await _send_games_message(
            message=message,
            text="Не удалось загрузить список игр.",
            edit_message=edit_message,
        )
        return True

    if not games and offset > 0:
        return False

    if not games:
        await _send_games_message(
            message=message,
            text=(
                "У тебя пока нет игр в коллекции.\n\n"
                "Нажми «Импорт из BGG», и я подтяну список из BoardGameGeek."
            ),
            edit_message=edit_message,
        )
        return True

    visible_games = games[:MY_GAMES_PAGE_SIZE]
    has_next_page = len(games) > MY_GAMES_PAGE_SIZE
    text = _format_my_games_text(visible_games, offset=offset)
    keyboard = get_my_games_keyboard(
        offset=offset,
        page_size=MY_GAMES_PAGE_SIZE,
        has_next_page=has_next_page,
    )
    await _send_games_message(
        message=message,
        text=text,
        edit_message=edit_message,
        reply_markup=keyboard,
    )
    return True


async def _send_games_message(
    *,
    message: Message,
    text: str,
    edit_message: bool,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if edit_message:
        await message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


def _format_my_games_text(games: list[dict], *, offset: int) -> str:
    page_number = offset // MY_GAMES_PAGE_SIZE + 1
    lines = ["<b>Мои игры</b>", f"Страница {page_number}", ""]

    for index, game in enumerate(games, start=offset + 1):
        lines.append(_format_game_line(index=index, game=game))

    return "\n\n".join(lines)


def _format_game_line(*, index: int, game: dict) -> str:
    title = escape(game["title"])
    players = _format_players(game["min_players"], game["max_players"])
    duration = _format_duration(game.get("play_time_minutes"))
    game_type = "База" if game.get("game_type") == "base" else "Дополнение"
    tags = [game_type]

    if game.get("has_campaign"):
        tags.append("кампания")

    details = ", ".join([players, duration, *tags])
    author = game.get("author")

    if author:
        return f"{index}. <b>{title}</b>\nАвтор: {escape(author)}\n{details}"

    return f"{index}. <b>{title}</b>\n{details}"


def _format_players(min_players: int, max_players: int) -> str:
    if min_players == max_players:
        return f"{min_players} игрок."
    return f"{min_players}-{max_players} игрок."


def _format_duration(play_time_minutes: int | None) -> str:
    if play_time_minutes is None:
        return "время не указано"
    return f"{play_time_minutes} мин"


def _parse_offset(callback_data: str | None) -> int | None:
    if callback_data is None:
        return None

    prefix = f"{MY_GAMES_CALLBACK_PREFIX}:"
    if not callback_data.startswith(prefix):
        return None

    value = callback_data.removeprefix(prefix)
    if not value.isdigit():
        return None

    return int(value)
