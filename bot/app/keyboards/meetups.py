from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.app.utils.meetup_datetime import format_meetup_datetime

MEETUP_CALLBACK_PREFIX = "meetup"
MEETUP_JOIN_CALLBACK_PREFIX = "meetup_join"
MEETUP_LEAVE_CALLBACK_PREFIX = "meetup_leave"
MEETUP_DELETE_CALLBACK_PREFIX = "meetup_delete"
MEETUP_DELETE_CONFIRM_CALLBACK_PREFIX = "meetup_delete_confirm"


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
        [InlineKeyboardButton(text="К списку встреч", callback_data=f"{MEETUP_CALLBACK_PREFIX}:list")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_group_meetup_keyboard(*, meetup_id: int, is_joined: bool) -> InlineKeyboardMarkup:
    if is_joined:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Не пойду",
                        callback_data=f"{MEETUP_LEAVE_CALLBACK_PREFIX}:{meetup_id}",
                    )
                ]
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Участвовать",
                    callback_data=f"{MEETUP_JOIN_CALLBACK_PREFIX}:{meetup_id}",
                )
            ]
        ]
    )


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
