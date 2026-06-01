from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.app.utils.meetup_datetime import format_meetup_datetime

MEETUP_CALLBACK_PREFIX = "meetup"
MEETUP_JOIN_CALLBACK_PREFIX = "meetup_join"
MEETUP_LEAVE_CALLBACK_PREFIX = "meetup_leave"
MEETUP_DELETE_CALLBACK_PREFIX = "meetup_delete"
MEETUP_DELETE_CONFIRM_CALLBACK_PREFIX = "meetup_delete_confirm"
MEETUP_CREATE_CONFIRM_CALLBACK = "meetup_create:confirm"
MEETUP_CREATE_BACK_CALLBACK = "meetup_create:back"
MEETUP_CREATE_CANCEL_CALLBACK = "meetup_create:cancel"
MEETUP_CREATE_SKIP_COMMENT_CALLBACK = "meetup_create:skip_comment"
MEETUP_CHAT_SELECTION_CALLBACK_PREFIX = "meetup_chat_select"
MEETUP_GAME_GROUP_CALLBACK_PREFIX = "meetup_game_group"
MEETUP_GAME_LETTER_CALLBACK_PREFIX = "meetup_game_letter"
MEETUP_GAME_PAGE_CALLBACK_PREFIX = "meetup_game_page"
MEETUP_GAME_TOGGLE_CALLBACK_PREFIX = "meetup_game_toggle"
MEETUP_GAME_DONE_CALLBACK = "meetup_game_done"
MEETUP_GAME_SKIP_CALLBACK = "meetup_game_skip"


def get_meetups_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать встречу"), KeyboardButton(text="Список встреч")],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
    )


def get_meetups_list_keyboard(meetups: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=_format_meetup_button_label(meetup),
                callback_data=f"{MEETUP_CALLBACK_PREFIX}:{meetup['id']}",
            )
        ]
        for meetup in meetups
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_meetup_detail_keyboard(
    meetup: dict,
    *,
    current_user_id: int,
    can_join: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if can_join:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Участвовать",
                    callback_data=f"{MEETUP_JOIN_CALLBACK_PREFIX}:{meetup['id']}",
                )
            ]
        )

    if meetup["creator_user_id"] == current_user_id:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Удалить",
                    callback_data=f"{MEETUP_DELETE_CALLBACK_PREFIX}:{meetup['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="К списку встреч",
                callback_data=f"{MEETUP_CALLBACK_PREFIX}:list",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_group_meetup_keyboard(*, meetup_id: int, is_joined: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Участвовать",
                    callback_data=f"{MEETUP_JOIN_CALLBACK_PREFIX}:{meetup_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Не пойду",
                    callback_data=f"{MEETUP_LEAVE_CALLBACK_PREFIX}:{meetup_id}",
                ),
            ]
        ]
    )


def get_create_meetup_step_keyboard(*, can_go_back: bool) -> InlineKeyboardMarkup:
    row: list[InlineKeyboardButton] = []
    if can_go_back:
        row.append(InlineKeyboardButton(text="Назад", callback_data=MEETUP_CREATE_BACK_CALLBACK))
    row.append(InlineKeyboardButton(text="Отмена", callback_data=MEETUP_CREATE_CANCEL_CALLBACK))
    return InlineKeyboardMarkup(inline_keyboard=[row])


def get_create_meetup_comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пропустить",
                    callback_data=MEETUP_CREATE_SKIP_COMMENT_CALLBACK,
                )
            ],
            [
                InlineKeyboardButton(text="Назад", callback_data=MEETUP_CREATE_BACK_CALLBACK),
                InlineKeyboardButton(text="Отмена", callback_data=MEETUP_CREATE_CANCEL_CALLBACK),
            ],
        ]
    )


def get_create_meetup_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Создать",
                    callback_data=MEETUP_CREATE_CONFIRM_CALLBACK,
                )
            ],
            [
                InlineKeyboardButton(text="Назад", callback_data=MEETUP_CREATE_BACK_CALLBACK),
                InlineKeyboardButton(text="Отмена", callback_data=MEETUP_CREATE_CANCEL_CALLBACK),
            ],
        ]
    )


def get_meetup_chat_selection_keyboard(chat_topics: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for topic in chat_topics:
        label = topic["title"] or str(topic["telegram_chat_id"])
        if len(label) > 50:
            label = f"{label[:47]}..."
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{MEETUP_CHAT_SELECTION_CALLBACK_PREFIX}:{topic['telegram_chat_id']}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_game_group_keyboard() -> InlineKeyboardMarkup:
    # coarse-grained groups to reduce initial choices
    groups = [
        ("A-G", "A-G"),
        ("H-N", "H-N"),
        ("O-U", "O-U"),
        ("V-Z", "V-Z"),
        ("RU", "RU"),
    ]
    rows = [[InlineKeyboardButton(text=label, callback_data=f"{MEETUP_GAME_GROUP_CALLBACK_PREFIX}:{value}") ] for label, value in groups]
    # Add a skip button to allow creating meetup without choosing games
    rows.append([InlineKeyboardButton(text="Пропустить выбор игр", callback_data=MEETUP_GAME_SKIP_CALLBACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_letters_keyboard(letters: list[str], *, selected_ids: set[int] | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, ch in enumerate(letters):
        row.append(InlineKeyboardButton(text=ch, callback_data=f"{MEETUP_GAME_LETTER_CALLBACK_PREFIX}:{ch}"))
        if (i + 1) % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    if selected_ids:
        rows.append([InlineKeyboardButton(text="Готово", callback_data=MEETUP_GAME_DONE_CALLBACK)])
    rows.append([InlineKeyboardButton(text="Пропустить выбор игр", callback_data=MEETUP_GAME_SKIP_CALLBACK)])
    rows.append([InlineKeyboardButton(text="Назад", callback_data=MEETUP_CREATE_BACK_CALLBACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_games_list_keyboard(games: list[dict], selected_ids: set[int], page: int, has_more: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for game in games:
        gid = game.get("id")
        title = game.get("title") or str(gid)
        prefix = "✅ " if gid in selected_ids else ""
        rows.append([InlineKeyboardButton(text=f"{prefix}{title}", callback_data=f"{MEETUP_GAME_TOGGLE_CALLBACK_PREFIX}:{gid}")])

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="<- Назад", callback_data=f"{MEETUP_GAME_PAGE_CALLBACK_PREFIX}:{page-1}"))
    if has_more:
        nav_row.append(InlineKeyboardButton(text="Вперед ->", callback_data=f"{MEETUP_GAME_PAGE_CALLBACK_PREFIX}:{page+1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="Готово", callback_data=MEETUP_GAME_DONE_CALLBACK)])
    rows.append([InlineKeyboardButton(text="Пропустить выбор игр", callback_data=MEETUP_GAME_SKIP_CALLBACK)])
    rows.append([InlineKeyboardButton(text="Назад", callback_data=MEETUP_CREATE_BACK_CALLBACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_meetup_delete_confirm_keyboard(meetup_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=f"{MEETUP_DELETE_CONFIRM_CALLBACK_PREFIX}:{meetup_id}",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"{MEETUP_CALLBACK_PREFIX}:{meetup_id}",
                ),
            ]
        ]
    )


def _format_meetup_button_label(meetup: dict) -> str:
    date_label = format_meetup_datetime(meetup["scheduled_at"])
    joined_count = len(meetup.get("participants", []))
    capacity = meetup["capacity_total"]
    return f"{date_label} ({joined_count}/{capacity})"
