from collections import defaultdict
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

BACKEND_GAMES_BATCH_SIZE = 100


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
        owned_games = await _load_owned_games(backend_client, owner_id=profile["id"])
    except httpx.HTTPError:
        await _send_games_message(
            message=message,
            text="Не удалось загрузить список игр.",
            edit_message=edit_message,
        )
        return True

    grouped_entries = _group_owned_games(owned_games)

    if not grouped_entries and offset > 0:
        return False

    if not grouped_entries:
        await _send_games_message(
            message=message,
            text=(
                "У тебя пока нет игр в коллекции.\n\n"
                "Нажми «Импорт из BGG», и я подтяну список из BoardGameGeek."
            ),
            edit_message=edit_message,
        )
        return True

    visible_entries = grouped_entries[offset : offset + MY_GAMES_PAGE_SIZE]
    if not visible_entries and offset > 0:
        return False

    has_next_page = offset + MY_GAMES_PAGE_SIZE < len(grouped_entries)
    text = _format_my_games_text(visible_entries, offset=offset)
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


async def _load_owned_games(
    backend_client: BackendAPIClient,
    *,
    owner_id: int,
) -> list[dict]:
    games: list[dict] = []
    offset = 0

    while True:
        batch = await backend_client.list_games(
            owner_id=owner_id,
            limit=BACKEND_GAMES_BATCH_SIZE,
            offset=offset,
        )
        games.extend(batch)
        if len(batch) < BACKEND_GAMES_BATCH_SIZE:
            return games
        offset += BACKEND_GAMES_BATCH_SIZE


def _group_owned_games(games: list[dict]) -> list[dict]:
    base_games_by_bgg_id = {
        game["bgg_id"]: game
        for game in games
        if game.get("game_type") == "base"
    }
    owned_expansions_by_base_id: dict[int, list[dict]] = defaultdict(list)
    attached_expansion_ids: set[int] = set()

    for game in games:
        if game.get("game_type") != "expansion":
            continue

        matched_base_games = _match_owned_base_games(
            game,
            base_games_by_bgg_id=base_games_by_bgg_id,
        )
        if len(matched_base_games) != 1:
            continue

        base_game = matched_base_games[0]
        owned_expansions_by_base_id[base_game["id"]].append(game)
        attached_expansion_ids.add(game["id"])

    entries: list[dict] = []
    for game in games:
        if game.get("game_type") == "base":
            expansions = sorted(
                owned_expansions_by_base_id.get(game["id"], []),
                key=lambda item: item["title"].lower(),
            )
            entries.append(_build_grouped_entry(game, expansions))
            continue

        if game["id"] not in attached_expansion_ids:
            entries.append(_build_grouped_entry(game, []))

    return entries


def _match_owned_base_games(
    game: dict,
    *,
    base_games_by_bgg_id: dict[int, dict],
) -> list[dict]:
    matched_base_games: list[dict] = []
    for base_bgg_id in game.get("bgg_expands_ids_cached") or []:
        base_game = base_games_by_bgg_id.get(base_bgg_id)
        if base_game is not None:
            matched_base_games.append(base_game)
    return matched_base_games


def _build_grouped_entry(game: dict, expansions: list[dict]) -> dict:
    display_max_players = game["max_players"]
    if game.get("game_type") == "base":
        for expansion in expansions:
            extra_players = max(expansion["max_players"] - game["max_players"], 0)
            display_max_players += extra_players

    return {
        "game": game,
        "expansions": expansions,
        "display_min_players": game["min_players"],
        "display_max_players": display_max_players,
    }


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


def _format_my_games_text(entries: list[dict], *, offset: int) -> str:
    page_number = offset // MY_GAMES_PAGE_SIZE + 1
    lines = ["<b>Мои игры</b>", f"Страница {page_number}", ""]

    for index, entry in enumerate(entries, start=offset + 1):
        lines.append(_format_grouped_game_line(index=index, entry=entry))

    return "\n\n".join(lines)


def _format_grouped_game_line(*, index: int, entry: dict) -> str:
    game = entry["game"]
    title = escape(game["title"])
    players = _format_players(entry["display_min_players"], entry["display_max_players"])
    duration = _format_duration(game.get("play_time_minutes"))
    game_type = "База" if game.get("game_type") == "base" else "Дополнение"
    tags = [game_type]

    if game.get("has_campaign"):
        tags.append("кампания")

    details = ", ".join([players, duration, *tags])
    author = game.get("author")
    lines = [f"{index}. <b>{title}</b>"]

    if author:
        lines.append(f"Автор: {escape(author)}")

    lines.append(details)

    expansions = entry["expansions"]
    if expansions:
        expansion_titles = ", ".join(escape(expansion["title"]) for expansion in expansions)
        lines.append(f"Допы: {expansion_titles}")

    return "\n".join(lines)


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
