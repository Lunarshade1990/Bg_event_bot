from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MY_GAMES_PAGE_SIZE = 5
MY_GAMES_CALLBACK_PREFIX = "my_games"

OTHER_USERS_PAGE_SIZE = 8
OTHER_USERS_CALLBACK_PREFIX = "other_users"
OTHER_GAMES_CALLBACK_PREFIX = "other_games"


def get_my_games_keyboard(
    *,
    offset: int,
    page_size: int = MY_GAMES_PAGE_SIZE,
    has_next_page: bool,
) -> InlineKeyboardMarkup | None:
    buttons: list[InlineKeyboardButton] = []

    if offset > 0:
        previous_offset = max(offset - page_size, 0)
        buttons.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"{MY_GAMES_CALLBACK_PREFIX}:{previous_offset}",
            )
        )

    if has_next_page:
        next_offset = offset + page_size
        buttons.append(
            InlineKeyboardButton(
                text="Вперед →",
                callback_data=f"{MY_GAMES_CALLBACK_PREFIX}:{next_offset}",
            )
        )

    if not buttons:
        return None

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def get_other_users_keyboard(
    users: list[dict],
    *,
    offset: int,
    page_size: int = OTHER_USERS_PAGE_SIZE,
    has_next_page: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=_format_user_button_label(user),
                callback_data=f"{OTHER_GAMES_CALLBACK_PREFIX}:{user['id']}:0",
            )
        ]
        for user in users
    ]

    nav_buttons: list[InlineKeyboardButton] = []
    if offset > 0:
        previous_offset = max(offset - page_size, 0)
        nav_buttons.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"{OTHER_USERS_CALLBACK_PREFIX}:{previous_offset}",
            )
        )
    if has_next_page:
        next_offset = offset + page_size
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед →",
                callback_data=f"{OTHER_USERS_CALLBACK_PREFIX}:{next_offset}",
            )
        )
    if nav_buttons:
        rows.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_other_user_games_keyboard(
    *,
    user_id: int,
    offset: int,
    page_size: int = MY_GAMES_PAGE_SIZE,
    has_next_page: bool,
) -> InlineKeyboardMarkup | None:
    buttons: list[InlineKeyboardButton] = []

    if offset > 0:
        previous_offset = max(offset - page_size, 0)
        buttons.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"{OTHER_GAMES_CALLBACK_PREFIX}:{user_id}:{previous_offset}",
            )
        )

    if has_next_page:
        next_offset = offset + page_size
        buttons.append(
            InlineKeyboardButton(
                text="Вперед →",
                callback_data=f"{OTHER_GAMES_CALLBACK_PREFIX}:{user_id}:{next_offset}",
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text="К списку игроков",
            callback_data=f"{OTHER_USERS_CALLBACK_PREFIX}:0",
        )
    )

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def _format_user_button_label(user: dict) -> str:
    username = user.get("username")
    display_name = user.get("display_name") or "Игрок"
    bgg_username = user.get("bgg_username")

    if username:
        label = f"@{username}"
    else:
        label = display_name

    if bgg_username and not username:
        label = f"{label} ({bgg_username})"

    return label[:64]
