import httpx
from aiogram import F, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputRichBlockParagraph,
    InputRichBlockPhoto,
    InputRichBlockSectionHeading,
    InputRichBlockSlideshow,
    InputRichMessage,
    Message,
    RichTextBold,
)

from bot.app.keyboards.games import (
    MY_GAMES_CALLBACK_PREFIX,
    MY_GAMES_PAGE_SIZE,
    OTHER_GAMES_CALLBACK_PREFIX,
    OTHER_USERS_CALLBACK_PREFIX,
    OTHER_USERS_PAGE_SIZE,
    get_my_games_keyboard,
    get_other_user_games_keyboard,
    get_other_users_keyboard,
)
from bot.app.services.backend_api import BackendAPIClient
from bot.app.services.game_service import load_owned_games
from bot.app.services.rich_message_media import load_game_cover_photos

router = Router(name="games")


@router.message(F.text == "Мои игры")
async def show_my_games(message: Message) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    await _render_my_games_page(message=message, telegram_id=user.id, offset=0)


@router.message(F.text == "Игры других")
async def show_other_users(message: Message) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    await _render_other_users_page(message=message, telegram_id=user.id, offset=0)


@router.callback_query(F.data.startswith(f"{MY_GAMES_CALLBACK_PREFIX}:"))
async def paginate_my_games(callback: CallbackQuery) -> None:
    user = callback.from_user
    message = callback.message

    if not isinstance(message, Message):
        await callback.answer("Не удалось обновить список игр.", show_alert=True)
        return

    offset = _parse_single_offset(callback.data, MY_GAMES_CALLBACK_PREFIX)
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


@router.callback_query(F.data.startswith(f"{OTHER_USERS_CALLBACK_PREFIX}:"))
async def paginate_other_users(callback: CallbackQuery) -> None:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer("Не удалось обновить список.", show_alert=True)
        return

    offset = _parse_single_offset(callback.data, OTHER_USERS_CALLBACK_PREFIX)
    if offset is None:
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    await _render_other_users_page(
        message=message,
        telegram_id=callback.from_user.id,
        offset=offset,
        edit_message=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{OTHER_GAMES_CALLBACK_PREFIX}:"))
async def show_other_user_games(callback: CallbackQuery) -> None:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer("Не удалось открыть коллекцию.", show_alert=True)
        return

    parsed = _parse_other_games_callback(callback.data)
    if parsed is None:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    user_id, offset = parsed
    page_rendered = await _render_other_user_games_page(
        message=message,
        owner_user_id=user_id,
        offset=offset,
        edit_message=True,
    )

    if not page_rendered:
        previous_offset = max(offset - MY_GAMES_PAGE_SIZE, 0)
        if previous_offset != offset:
            await callback.answer("Список игр изменился, показываю предыдущую страницу.")
            await _render_other_user_games_page(
                message=message,
                owner_user_id=user_id,
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

    return await _render_user_games_page(
        message=message,
        owner_user_id=profile["id"],
        title="Мои игры",
        empty_text=(
            "У тебя пока нет игр в коллекции.\n\n"
            "Нажми «Импорт из BGG», и я подтяну список из BoardGameGeek."
        ),
        offset=offset,
        edit_message=edit_message,
        keyboard_factory=lambda current_offset, has_next_page: get_my_games_keyboard(
            offset=current_offset,
            page_size=MY_GAMES_PAGE_SIZE,
            has_next_page=has_next_page,
        ),
    )


async def _render_other_users_page(
    *,
    message: Message,
    telegram_id: int,
    offset: int,
    edit_message: bool = False,
) -> None:
    backend_client = BackendAPIClient()

    try:
        profile = await backend_client.get_user_by_telegram_id(telegram_id)
    except httpx.HTTPError:
        await _send_games_message(
            message=message,
            text="Не удалось связаться с backend API.",
            edit_message=edit_message,
        )
        return

    if profile is None:
        await _send_games_message(
            message=message,
            text="Я не нашел твой профиль. Нажми /start, чтобы синхронизироваться с backend.",
            edit_message=edit_message,
        )
        return

    try:
        users = await backend_client.list_users_with_games(
            exclude_user_id=profile["id"],
            limit=OTHER_USERS_PAGE_SIZE + 1,
            offset=offset,
        )
    except httpx.HTTPError:
        await _send_games_message(
            message=message,
            text="Не удалось загрузить список игроков.",
            edit_message=edit_message,
        )
        return

    has_next_page = len(users) > OTHER_USERS_PAGE_SIZE
    visible_users = users[:OTHER_USERS_PAGE_SIZE]

    if not visible_users:
        await _send_games_message(
            message=message,
            text=(
                "Пока нет других игроков с импортированными коллекциями.\n\n"
                "Когда кто-то импортирует игры из BGG, он появится здесь."
            ),
            edit_message=edit_message,
        )
        return

    page_number = offset // OTHER_USERS_PAGE_SIZE + 1
    text = "\n".join(
        [
            "<b>Игры других</b>",
            f"Страница {page_number}",
            "",
            "Выбери игрока, чтобы посмотреть его коллекцию:",
        ]
    )
    keyboard = get_other_users_keyboard(
        visible_users,
        offset=offset,
        page_size=OTHER_USERS_PAGE_SIZE,
        has_next_page=has_next_page,
    )
    await _send_games_message(
        message=message,
        text=text,
        edit_message=edit_message,
        reply_markup=keyboard,
    )


async def _render_other_user_games_page(
    *,
    message: Message,
    owner_user_id: int,
    offset: int,
    edit_message: bool = False,
) -> bool:
    backend_client = BackendAPIClient()

    try:
        owner = await backend_client.get_user(owner_user_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await _send_games_message(
                message=message,
                text="Игрок не найден.",
                edit_message=edit_message,
            )
            return True
        await _send_games_message(
            message=message,
            text="Не удалось загрузить профиль игрока.",
            edit_message=edit_message,
        )
        return True
    except httpx.HTTPError:
        await _send_games_message(
            message=message,
            text="Не удалось связаться с backend API.",
            edit_message=edit_message,
        )
        return True

    owner_label = _format_user_display_name(owner)
    return await _render_user_games_page(
        message=message,
        owner_user_id=owner_user_id,
        title=f"Игры: {owner_label}",
        empty_text=f"У {owner_label} пока нет игр в коллекции.",
        offset=offset,
        edit_message=edit_message,
        keyboard_factory=lambda current_offset, has_next_page: get_other_user_games_keyboard(
            user_id=owner_user_id,
            offset=current_offset,
            page_size=MY_GAMES_PAGE_SIZE,
            has_next_page=has_next_page,
        ),
    )


async def _render_user_games_page(
    *,
    message: Message,
    owner_user_id: int,
    title: str,
    empty_text: str,
    offset: int,
    edit_message: bool,
    keyboard_factory,
) -> bool:
    try:
        grouped_entries = await load_owned_games(owner_user_id)
    except httpx.HTTPError:
        await _send_games_message(
            message=message,
            text="Не удалось загрузить список игр.",
            edit_message=edit_message,
        )
        return True

    if not grouped_entries and offset > 0:
        return False

    if not grouped_entries:
        await _send_games_message(
            message=message,
            text=empty_text,
            edit_message=edit_message,
        )
        return True

    visible_entries = grouped_entries[offset : offset + MY_GAMES_PAGE_SIZE]
    if not visible_entries and offset > 0:
        return False

    has_next_page = offset + MY_GAMES_PAGE_SIZE < len(grouped_entries)
    game_photos = await load_game_cover_photos([entry["game"] for entry in visible_entries])
    rich_message = _build_games_rich_message(
        title=title,
        entries=visible_entries,
        offset=offset,
        game_photos=game_photos,
    )
    keyboard = keyboard_factory(offset, has_next_page)
    await _send_games_rich_message(
        message=message,
        rich_message=rich_message,
        edit_message=edit_message,
        reply_markup=keyboard,
    )
    return True


async def _send_games_rich_message(
    *,
    message: Message,
    rich_message: InputRichMessage,
    edit_message: bool,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if edit_message:
        await message.edit_text(rich_message=rich_message, reply_markup=reply_markup)
        return

    bot = message.bot
    if bot is None:
        raise RuntimeError("Cannot send a rich games message without a bot instance.")

    await bot.send_rich_message(
        chat_id=message.chat.id,
        rich_message=rich_message,
        reply_markup=reply_markup,
    )


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


def _build_games_rich_message(
    *,
    title: str,
    entries: list[dict],
    offset: int,
    game_photos: list[BufferedInputFile | None],
) -> InputRichMessage:
    page_number = offset // MY_GAMES_PAGE_SIZE + 1
    blocks = [
        InputRichBlockSectionHeading(text=title, size=2),
        InputRichBlockParagraph(text=f"Страница {page_number}"),
    ]
    photo_blocks = []

    for index, (entry, photo) in enumerate(
        zip(entries, game_photos, strict=True),
        start=offset + 1,
    ):
        game = entry["game"]
        blocks.append(
            InputRichBlockParagraph(
                text=RichTextBold(text=f"{index}. {game.get('title') or 'Игра'}")
            )
        )
        if photo is not None:
            photo_blocks.append(InputRichBlockPhoto(photo=InputMediaPhoto(media=photo)))
        details = _format_grouped_game_details(entry)
        if details:
            blocks.append(InputRichBlockParagraph(text="\n".join(details)))

    if photo_blocks:
        blocks.append(InputRichBlockSlideshow(blocks=photo_blocks))

    return InputRichMessage(blocks=blocks)


def _format_user_display_name(user: dict) -> str:
    username = user.get("username")
    display_name = user.get("display_name") or "Игрок"
    if username:
        return f"@{username}"
    return display_name


def _format_grouped_game_details(entry: dict) -> list[str]:
    game = entry["game"]
    players = _format_players(entry["display_min_players"], entry["display_max_players"])
    duration = _format_duration(game.get("play_time_minutes"))
    game_type = "База" if game.get("game_type") == "base" else "Дополнение"
    tags = [game_type]

    if game.get("has_campaign"):
        tags.append("кампания")

    details = ", ".join([players, duration, *tags])
    author = game.get("author")
    lines: list[str] = []

    if author:
        lines.append(f"Автор: {author}")

    lines.append(details)

    expansions = entry["expansions"]
    if expansions:
        expansion_titles = ", ".join(
            str(expansion.get("title") or "Дополнение") for expansion in expansions
        )
        lines.append(f"Допы: {expansion_titles}")

    return lines


def _format_players(min_players: int, max_players: int) -> str:
    if min_players == max_players:
        return f"{min_players} игрок."
    return f"{min_players}-{max_players} игрок."


def _format_duration(play_time_minutes: int | None) -> str:
    if play_time_minutes is None:
        return "время не указано"
    return f"{play_time_minutes} мин"


def _parse_single_offset(callback_data: str | None, prefix: str) -> int | None:
    if callback_data is None:
        return None

    expected_prefix = f"{prefix}:"
    if not callback_data.startswith(expected_prefix):
        return None

    value = callback_data.removeprefix(expected_prefix)
    if not value.isdigit():
        return None

    return int(value)


def _parse_other_games_callback(callback_data: str | None) -> tuple[int, int] | None:
    if callback_data is None:
        return None

    expected_prefix = f"{OTHER_GAMES_CALLBACK_PREFIX}:"
    if not callback_data.startswith(expected_prefix):
        return None

    parts = callback_data.removeprefix(expected_prefix).split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None

    return int(parts[0]), int(parts[1])
