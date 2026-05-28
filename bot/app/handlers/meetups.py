import logging
from html import escape
from typing import cast

import httpx
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from backend.app.core.config import get_settings
from bot.app.keyboards.main_menu import get_main_menu_keyboard
from bot.app.keyboards.meetups import (
    MEETUP_CALLBACK_PREFIX,
    MEETUP_CREATE_BACK_CALLBACK,
    MEETUP_CREATE_CANCEL_CALLBACK,
    MEETUP_CREATE_CONFIRM_CALLBACK,
    MEETUP_CREATE_SKIP_COMMENT_CALLBACK,
    MEETUP_DELETE_CALLBACK_PREFIX,
    MEETUP_DELETE_CONFIRM_CALLBACK_PREFIX,
    MEETUP_JOIN_CALLBACK_PREFIX,
    MEETUP_LEAVE_CALLBACK_PREFIX,
    get_create_meetup_comment_keyboard,
    get_create_meetup_confirm_keyboard,
    get_create_meetup_step_keyboard,
    get_group_meetup_keyboard,
    get_meetup_delete_confirm_keyboard,
    get_meetup_detail_keyboard,
    get_meetups_list_keyboard,
    get_meetups_menu_keyboard,
)
from bot.app.services.backend_api import BackendAPIClient
from bot.app.states.create_meetup import CreateMeetupStates
from bot.app.utils.meetup_datetime import (
    MEETUP_DATETIME_EXAMPLE,
    format_meetup_datetime,
    is_future_meetup_datetime,
    parse_meetup_datetime,
)

router = Router(name="meetups")

SKIP_COMMENT_VALUES = {"-", "пропустить", "skip"}

_topic_thread_cache: dict[int, int] = {}


@router.message(F.text == "Встречи")
async def open_meetups_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Раздел встреч:", reply_markup=get_meetups_menu_keyboard())


@router.message(Command("meetup"))
async def start_group_meetup(message: Message, state: FSMContext) -> None:
    chat = message.chat
    if chat.type not in {"group", "supergroup"}:
        await message.answer("Эта команда работает только в группе.")
        return

    settings = get_settings()
    target_chat_id = settings.telegram_group_id or chat.id
    topic_name = settings.telegram_topic_name
    if not topic_name:
        await message.answer("Не задан TELEGRAM_TOPIC_NAME в .env.")
        return

    backend_client = BackendAPIClient()
    target_thread_id = await _ensure_forum_topic_thread_id(
        bot=message.bot,
        chat_id=target_chat_id,
        topic_name=topic_name,
        backend_client=backend_client,
    )
    if target_thread_id is None:
        await message.answer(
            "Не удалось найти/создать тему для встреч. "
            "Проверь, что включены Topics и у бота есть право manage topics."
        )
        return

    await state.clear()
    await state.update_data(
        group_mode=True,
        telegram_chat_id=target_chat_id,
        telegram_thread_id=target_thread_id,
    )
    await _record_creation_message(state, message.message_id)
    await state.set_state(CreateMeetupStates.waiting_for_date)
    await _send_creation_prompt(
        message,
        state,
        _get_date_prompt_text(group_mode=True),
        reply_markup=get_create_meetup_step_keyboard(can_go_back=False),
    )


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, bot: Bot) -> None:
    chat = event.chat
    if chat.type not in {"group", "supergroup"}:
        return

    if event.new_chat_member.status not in {"member", "administrator"}:
        return

    settings = get_settings()
    topic_name = settings.telegram_topic_name
    if not topic_name:
        return

    backend_client = BackendAPIClient()
    thread_id = await _ensure_forum_topic_thread_id(
        bot=bot,
        chat_id=chat.id,
        topic_name=topic_name,
        backend_client=backend_client,
    )
    if thread_id is None:
        logger = logging.getLogger(__name__)
        logger.warning("Failed to ensure forum topic for chat %s", chat.id)
        try:
            await bot.send_message(
                chat.id,
                (
                    "Не удалось автоматически создать тему для встреч. "
                    "Проверьте, что в группе включены Topics и у бота есть право "
                    "manage topics (админ с соответствующим правом)."
                ),
            )
        except Exception:
            logger.exception("Failed to send failure notification to chat %s", chat.id)


@router.message(F.text == "Назад")
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())


@router.message(F.text == "Создать встречу")
async def start_create_meetup(message: Message, state: FSMContext) -> None:
    if not await _ensure_profile(message):
        return

    await state.clear()
    await _record_creation_message(state, message.message_id)
    await state.set_state(CreateMeetupStates.waiting_for_date)
    await _send_creation_prompt(
        message,
        state,
        _get_date_prompt_text(group_mode=False),
        reply_markup=get_create_meetup_step_keyboard(can_go_back=False),
    )


@router.message(CreateMeetupStates.waiting_for_date)
async def receive_meetup_date(message: Message, state: FSMContext) -> None:
    await _record_creation_message(state, message.message_id)

    parsed = parse_meetup_datetime(message.text or "")
    if parsed is None:
        await _send_creation_prompt(
            message,
            state,
            "Не удалось разобрать дату. Пример: "
            f"<code>{MEETUP_DATETIME_EXAMPLE}</code>",
            reply_markup=get_create_meetup_step_keyboard(can_go_back=False),
        )
        return

    if not is_future_meetup_datetime(parsed):
        await _send_creation_prompt(
            message,
            state,
            "Дата и время встречи должны быть в будущем. Попробуй еще раз.",
            reply_markup=get_create_meetup_step_keyboard(can_go_back=False),
        )
        return

    await state.update_data(scheduled_at=parsed.isoformat())
    await state.set_state(CreateMeetupStates.waiting_for_capacity)
    await _send_creation_prompt(
        message,
        state,
        _get_capacity_prompt_text(),
        reply_markup=get_create_meetup_step_keyboard(can_go_back=True),
    )


@router.message(CreateMeetupStates.waiting_for_capacity)
async def receive_meetup_capacity(message: Message, state: FSMContext) -> None:
    await _record_creation_message(state, message.message_id)

    raw_value = (message.text or "").strip()
    if not raw_value.isdigit():
        await _send_creation_prompt(
            message,
            state,
            "Нужно целое число, например: 4",
            reply_markup=get_create_meetup_step_keyboard(can_go_back=True),
        )
        return

    capacity_total = int(raw_value)
    if capacity_total < 1:
        await _send_creation_prompt(
            message,
            state,
            "Вместимость должна быть не меньше 1.",
            reply_markup=get_create_meetup_step_keyboard(can_go_back=True),
        )
        return

    await state.update_data(capacity_total=capacity_total)
    await state.set_state(CreateMeetupStates.waiting_for_comment)
    await _send_creation_prompt(
        message,
        state,
        _get_comment_prompt_text(),
        reply_markup=get_create_meetup_comment_keyboard(),
    )


@router.message(CreateMeetupStates.waiting_for_comment)
async def receive_meetup_comment(message: Message, state: FSMContext) -> None:
    await _record_creation_message(state, message.message_id)

    raw_comment = (message.text or "").strip()
    comment = None if raw_comment.lower() in SKIP_COMMENT_VALUES else raw_comment

    data = await state.get_data()
    scheduled_at = data.get("scheduled_at")
    capacity_total = data.get("capacity_total")
    if scheduled_at is None or capacity_total is None:
        await state.clear()
        await message.answer(
            "Данные встречи потерялись. Начни создание заново.",
            reply_markup=get_meetups_menu_keyboard(),
        )
        return

    await state.update_data(comment=comment)
    await state.set_state(CreateMeetupStates.waiting_for_confirmation)
    await _send_creation_prompt(
        message,
        state,
        _format_create_meetup_confirmation(
            scheduled_at=scheduled_at,
            capacity_total=capacity_total,
            comment=comment,
        ),
        reply_markup=get_create_meetup_confirm_keyboard(),
    )


@router.callback_query(F.data == MEETUP_CREATE_SKIP_COMMENT_CALLBACK)
async def skip_create_meetup_comment(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    scheduled_at = data.get("scheduled_at")
    capacity_total = data.get("capacity_total")
    if scheduled_at is None or capacity_total is None:
        await state.clear()
        await callback.answer("Данные встречи потерялись. Начни создание заново.", show_alert=True)
        return

    await state.update_data(comment=None)
    await state.set_state(CreateMeetupStates.waiting_for_confirmation)
    await _edit_creation_prompt(
        callback,
        state,
        _format_create_meetup_confirmation(
            scheduled_at=scheduled_at,
            capacity_total=capacity_total,
            comment=None,
        ),
        reply_markup=get_create_meetup_confirm_keyboard(),
    )


@router.message(CreateMeetupStates.waiting_for_confirmation)
async def receive_meetup_confirmation_text(message: Message, state: FSMContext) -> None:
    await _record_creation_message(state, message.message_id)

    data = await state.get_data()
    scheduled_at = data.get("scheduled_at")
    capacity_total = data.get("capacity_total")
    if scheduled_at is None or capacity_total is None:
        await state.clear()
        await message.answer(
            "Данные встречи потерялись. Начни создание заново.",
            reply_markup=get_meetups_menu_keyboard(),
        )
        return

    await _send_creation_prompt(
        message,
        state,
        _format_create_meetup_confirmation(
            scheduled_at=scheduled_at,
            capacity_total=capacity_total,
            comment=data.get("comment"),
            prefix="Почти готово. Нажми кнопку, чтобы создать встречу.",
        ),
        reply_markup=get_create_meetup_confirm_keyboard(),
    )


@router.callback_query(F.data == MEETUP_CREATE_BACK_CALLBACK)
async def back_create_meetup(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == CreateMeetupStates.waiting_for_capacity.state:
        await state.update_data(scheduled_at=None)
        await state.set_state(CreateMeetupStates.waiting_for_date)
        await _edit_creation_prompt(
            callback,
            state,
            _get_date_prompt_text(group_mode=bool(data.get("group_mode"))),
            reply_markup=get_create_meetup_step_keyboard(can_go_back=False),
        )
        return

    if current_state == CreateMeetupStates.waiting_for_comment.state:
        await state.update_data(capacity_total=None)
        await state.set_state(CreateMeetupStates.waiting_for_capacity)
        await _edit_creation_prompt(
            callback,
            state,
            _get_capacity_prompt_text(),
            reply_markup=get_create_meetup_step_keyboard(can_go_back=True),
        )
        return

    if current_state == CreateMeetupStates.waiting_for_confirmation.state:
        await state.update_data(comment=None)
        await state.set_state(CreateMeetupStates.waiting_for_comment)
        await _edit_creation_prompt(
            callback,
            state,
            _get_comment_prompt_text(),
            reply_markup=get_create_meetup_comment_keyboard(),
        )
        return

    await callback.answer("Назад отсюда перейти нельзя.", show_alert=True)


@router.callback_query(F.data == MEETUP_CREATE_CANCEL_CALLBACK)
async def cancel_create_meetup(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    message = callback.message
    await state.clear()

    if message is None:
        await callback.answer("Создание встречи отменено.")
        return

    msg = cast(Message, message)
    if _is_group_creation(data=data, message=msg):
        await callback.answer("Создание встречи отменено.")
        await _delete_creation_messages(
            msg.bot,
            _get_creation_chat_id(data, msg),
            _get_creation_message_ids(data, msg.message_id),
        )
        return

    await msg.edit_text("Создание встречи отменено.")
    await callback.answer("Создание встречи отменено.")


@router.callback_query(F.data == MEETUP_CREATE_CONFIRM_CALLBACK)
async def confirm_create_meetup(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    scheduled_at = data.get("scheduled_at")
    capacity_total = data.get("capacity_total")
    if scheduled_at is None or capacity_total is None:
        await state.clear()
        await callback.answer("Данные встречи потерялись. Начни создание заново.", show_alert=True)
        return

    backend_client = BackendAPIClient()
    profile = await _ensure_profile_for_user_callback(callback, backend_client=backend_client)
    if profile is None:
        return

    telegram_chat_id = data.get("telegram_chat_id")
    telegram_thread_id = data.get("telegram_thread_id")
    try:
        meetup = await backend_client.create_meetup(
            creator_user_id=profile["id"],
            scheduled_at=scheduled_at,
            capacity_total=capacity_total,
            comment=data.get("comment"),
            telegram_chat_id=telegram_chat_id,
            telegram_thread_id=telegram_thread_id,
        )
    except httpx.HTTPStatusError as exc:
        await callback.answer(
            f"Не удалось создать встречу: {_extract_error_detail(exc)}",
            show_alert=True,
        )
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return

    message = callback.message
    await state.clear()
    if telegram_chat_id and telegram_thread_id:
        if message is None:
            await callback.answer("Не удалось отправить сообщение в тему.", show_alert=True)
            return
        msg = cast(Message, message)
        sent = await msg.bot.send_message(
            chat_id=telegram_chat_id,
            message_thread_id=telegram_thread_id,
            text=_format_group_meetup_card(meetup),
            parse_mode="HTML",
            reply_markup=_build_group_keyboard_for_user(meetup, telegram_id=callback.from_user.id),
        )
        try:
            await backend_client.set_meetup_telegram_message_id(
                meetup["id"],
                telegram_message_id=sent.message_id,
            )
        except httpx.HTTPError:
            pass

        await callback.answer("Встреча создана и опубликована в теме.")
        await _delete_creation_messages(
            msg.bot,
            telegram_chat_id,
            _get_creation_message_ids(data, msg.message_id),
        )
        return

    if message is not None:
        msg = cast(Message, message)
        await msg.edit_text(
            _format_meetup_details(meetup),
            parse_mode="HTML",
        )
    await callback.answer("Встреча создана.")


@router.message(F.text == "Список встреч")
async def list_meetups(message: Message) -> None:
    if not await _ensure_profile(message):
        return

    await _send_meetups_list(message)


@router.callback_query(F.data == f"{MEETUP_CALLBACK_PREFIX}:list")
async def list_meetups_callback(callback: CallbackQuery) -> None:
    message = callback.message
    if message is None:
        await callback.answer("Не удалось обновить список.", show_alert=True)
        return

    await _send_meetups_list(cast(Message, message), edit_message=True)
    await callback.answer()


@router.callback_query(F.data.startswith(f"{MEETUP_CALLBACK_PREFIX}:"))
async def show_meetup_details(callback: CallbackQuery) -> None:
    if callback.data == f"{MEETUP_CALLBACK_PREFIX}:list":
        return

    meetup_id = _parse_meetup_id(callback.data, MEETUP_CALLBACK_PREFIX)
    if meetup_id is None:
        await callback.answer("Некорректная встреча.", show_alert=True)
        return

    await _render_meetup_details(callback, meetup_id)


@router.callback_query(F.data.startswith(f"{MEETUP_JOIN_CALLBACK_PREFIX}:"))
async def join_meetup(callback: CallbackQuery) -> None:
    meetup_id = _parse_meetup_id(callback.data, MEETUP_JOIN_CALLBACK_PREFIX)
    if meetup_id is None:
        await callback.answer("Некорректная встреча.", show_alert=True)
        return

    backend_client = BackendAPIClient()

    profile = await _ensure_profile_for_user_callback(callback, backend_client=backend_client)
    if profile is None:
        return

    try:
        await backend_client.join_meetup(meetup_id, user_id=profile["id"])
    except httpx.HTTPStatusError as exc:
        await callback.answer(_extract_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return

    await callback.answer("Ты записан на встречу.")
    await _render_meetup_details(callback, meetup_id)


@router.callback_query(F.data.startswith(f"{MEETUP_LEAVE_CALLBACK_PREFIX}:"))
async def leave_meetup(callback: CallbackQuery) -> None:
    meetup_id = _parse_meetup_id(callback.data, MEETUP_LEAVE_CALLBACK_PREFIX)
    if meetup_id is None:
        await callback.answer("Некорректная встреча.", show_alert=True)
        return

    backend_client = BackendAPIClient()
    profile = await _ensure_profile_for_user_callback(callback, backend_client=backend_client)
    if profile is None:
        return

    try:
        await backend_client.leave_meetup(meetup_id, user_id=profile["id"])
    except httpx.HTTPStatusError as exc:
        await callback.answer(_extract_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return

    await callback.answer("Участие отменено.")
    await _render_meetup_details(callback, meetup_id)


@router.callback_query(F.data.startswith(f"{MEETUP_DELETE_CALLBACK_PREFIX}:"))
async def confirm_delete_meetup(callback: CallbackQuery) -> None:
    meetup_id = _parse_meetup_id(callback.data, MEETUP_DELETE_CALLBACK_PREFIX)
    if meetup_id is None:
        await callback.answer("Некорректная встреча.", show_alert=True)
        return

    message = callback.message
    if message is None:
        await callback.answer("Не удалось открыть подтверждение.", show_alert=True)
        return

    msg = cast(Message, message)
    await msg.edit_text(
        "Удалить встречу? Это действие нельзя отменить.",
        reply_markup=get_meetup_delete_confirm_keyboard(meetup_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{MEETUP_DELETE_CONFIRM_CALLBACK_PREFIX}:"))
async def delete_meetup(callback: CallbackQuery) -> None:
    meetup_id = _parse_meetup_id(callback.data, MEETUP_DELETE_CONFIRM_CALLBACK_PREFIX)
    if meetup_id is None:
        await callback.answer("Некорректная встреча.", show_alert=True)
        return

    user = callback.from_user
    backend_client = BackendAPIClient()

    try:
        profile = await backend_client.get_user_by_telegram_id(user.id)
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return

    if profile is None:
        await callback.answer("Сначала нажми /start.", show_alert=True)
        return

    try:
        await backend_client.delete_meetup(meetup_id, requesting_user_id=profile["id"])
    except httpx.HTTPStatusError as exc:
        await callback.answer(_extract_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return

    message = callback.message
    if message is not None:
        msg = cast(Message, message)
        await msg.edit_text("Встреча удалена.")
    await callback.answer("Встреча удалена.")


async def _ensure_profile(message: Message) -> bool:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return False

    backend_client = BackendAPIClient()
    try:
        profile = await backend_client.get_user_by_telegram_id(user.id)
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return False

    if profile is None:
        await message.answer("Я не нашел твой профиль. Нажми /start, чтобы синхронизироваться.")
        return False

    return True


async def _send_meetups_list(message: Message, *, edit_message: bool = False) -> None:
    backend_client = BackendAPIClient()
    try:
        meetups = await backend_client.list_meetups()
    except httpx.HTTPError:
        text = "Не удалось загрузить список встреч."
        if edit_message:
            await message.edit_text(text)
        else:
            await message.answer(text, reply_markup=get_meetups_menu_keyboard())
        return

    if not meetups:
        text = "Пока нет запланированных встреч."
        if edit_message:
            await message.edit_text(text)
        else:
            await message.answer(text, reply_markup=get_meetups_menu_keyboard())
        return

    text = "Запланированные встречи:\nНажми на встречу, чтобы открыть детали."
    keyboard = get_meetups_list_keyboard(meetups)
    if edit_message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def _render_meetup_details(callback: CallbackQuery, meetup_id: int) -> None:
    message = callback.message
    if message is None:
        await callback.answer("Не удалось открыть встречу.", show_alert=True)
        return
    msg = cast(Message, message)

    user = callback.from_user
    backend_client = BackendAPIClient()

    try:
        profile = await backend_client.get_user_by_telegram_id(user.id)
        meetup = await backend_client.get_meetup(meetup_id)
    except httpx.HTTPStatusError as exc:
        await callback.answer(_extract_error_detail(exc), show_alert=True)
        return
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return

    if profile is None:
        await callback.answer("Сначала нажми /start.", show_alert=True)
        return

    is_group_context = message.chat.type in {"group", "supergroup"}
    if is_group_context:
        await msg.edit_text(
            _format_group_meetup_card(meetup),
            parse_mode="HTML",
            reply_markup=_build_group_keyboard_for_user(meetup, telegram_id=user.id),
        )
    else:
        joined_user_ids = {participant["telegram_id"] for participant in meetup["participants"]}
        can_join = (
            user.id not in joined_user_ids
            and len(meetup["participants"]) < meetup["capacity_total"]
        )
        await msg.edit_text(
            _format_meetup_details(meetup),
            parse_mode="HTML",
            reply_markup=get_meetup_detail_keyboard(
                meetup,
                current_user_id=profile["id"],
                can_join=can_join,
            ),
        )
    await callback.answer()


def _build_group_keyboard_for_user(meetup: dict, *, telegram_id: int):
    joined_user_ids = {participant["telegram_id"] for participant in meetup.get("participants", [])}
    is_joined = telegram_id in joined_user_ids
    return get_group_meetup_keyboard(meetup_id=meetup["id"], is_joined=is_joined)


def _format_group_meetup_card(meetup: dict) -> str:
    date_label = escape(format_meetup_datetime(meetup["scheduled_at"]))
    participants = meetup.get("participants", [])
    joined_count = len(participants)
    capacity = meetup["capacity_total"]
    free = max(capacity - joined_count, 0)

    participant_lines: list[str] = []
    for participant in participants:
        username = participant.get("username")
        display_name = participant.get("display_name") or "Участник"
        if username:
            participant_lines.append(f"- @{escape(username)}")
        else:
            participant_lines.append(f"- {escape(display_name)}")

    if not participant_lines:
        participant_lines = ["- пока нет участников"]

    lines = [
        f"<b>Встреча</b> (#{meetup['id']})",
        f"Дата: <code>{date_label}</code>",
        f"Свободно мест: <b>{free}</b> из {capacity}",
    ]
    comment = meetup.get("comment")
    if comment:
        lines.append(f"Комментарий: {escape(comment)}")
    lines.extend(["", "<b>Участники:</b>", *participant_lines])
    return "\n".join(lines)


def _get_date_prompt_text(*, group_mode: bool) -> str:
    prefix = "Создание встречи.\n" if group_mode else ""
    return (
        f"{prefix}Укажи дату и время встречи, например "
        f"<code>{MEETUP_DATETIME_EXAMPLE}</code> (UTC). "
        "Год можно не писать или указать полностью/двумя цифрами."
    )


def _get_capacity_prompt_text() -> str:
    return "Сколько всего игроков может участвовать? (число от 1)"


def _get_comment_prompt_text() -> str:
    return "Добавь комментарий к встрече или нажми «Пропустить»."


def _format_create_meetup_confirmation(
    *,
    scheduled_at: str,
    capacity_total: int,
    comment: str | None,
    prefix: str = "Проверь встречу перед публикацией.",
) -> str:
    date_label = escape(format_meetup_datetime(scheduled_at))
    lines = [
        prefix,
        f"Дата: <code>{date_label}</code>",
        f"Игроков: {capacity_total}",
    ]
    if comment:
        lines.append(f"Комментарий: {escape(comment)}")
    return "\n".join(lines)


async def _ensure_profile_for_user(
    message: Message,
    *,
    backend_client: BackendAPIClient,
) -> dict | None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return None

    try:
        await backend_client.sync_telegram_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        profile = await backend_client.get_user_by_telegram_id(user.id)
        return profile
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return None


async def _ensure_profile_for_user_callback(
    callback: CallbackQuery,
    *,
    backend_client: BackendAPIClient,
) -> dict | None:
    user = callback.from_user
    try:
        await backend_client.sync_telegram_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        profile = await backend_client.get_user_by_telegram_id(user.id)
        if profile is None:
            await callback.answer("Не удалось создать профиль пользователя.", show_alert=True)
        return profile
    except httpx.HTTPError:
        await callback.answer("Не удалось связаться с backend API.", show_alert=True)
        return None


async def _record_creation_message(state: FSMContext, message_id: int) -> None:
    data = await state.get_data()
    message_ids = data.get("creation_message_ids")
    if not isinstance(message_ids, list):
        message_ids = []
    if message_id not in message_ids:
        message_ids.append(message_id)
    await state.update_data(creation_message_ids=message_ids)


async def _send_creation_prompt(
    message: Message,
    state: FSMContext,
    text: str,
    *,
    reply_markup,
) -> None:
    data = await state.get_data()
    previous_prompt_id = data.get("creation_prompt_message_id")
    prompt = await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    await _record_creation_message(state, prompt.message_id)
    await state.update_data(creation_prompt_message_id=prompt.message_id)
    if isinstance(previous_prompt_id, int) and previous_prompt_id != prompt.message_id:
        await _delete_creation_messages(message.bot, message.chat.id, [previous_prompt_id])


async def _edit_creation_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    *,
    reply_markup,
) -> None:
    message = callback.message
    if message is None:
        await callback.answer("Не удалось обновить шаг создания встречи.", show_alert=True)
        return

    msg = cast(Message, message)
    await msg.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await _record_creation_message(state, msg.message_id)
    await state.update_data(creation_prompt_message_id=msg.message_id)
    await callback.answer()


def _is_group_creation(*, data: dict, message: Message) -> bool:
    has_group_target = bool(data.get("telegram_chat_id") and data.get("telegram_thread_id"))
    return has_group_target or message.chat.type in {"group", "supergroup"}


def _get_creation_chat_id(data: dict, message: Message) -> int:
    telegram_chat_id = data.get("telegram_chat_id")
    if isinstance(telegram_chat_id, int):
        return telegram_chat_id
    return message.chat.id


def _get_creation_message_ids(data: dict, *extra_message_ids: int) -> list[int]:
    raw_message_ids = data.get("creation_message_ids")
    message_ids = raw_message_ids if isinstance(raw_message_ids, list) else []
    result: list[int] = []
    for message_id in [*message_ids, *extra_message_ids]:
        if isinstance(message_id, int) and message_id not in result:
            result.append(message_id)
    return result


async def _delete_creation_messages(bot: Bot | None, chat_id: int, message_ids: list[int]) -> None:
    if bot is None:
        return
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass


async def _ensure_forum_topic_thread_id(
    *,
    bot: Bot | None,
    chat_id: int,
    topic_name: str,
    backend_client: BackendAPIClient,
) -> int | None:
    if bot is None:
        return None
    cached = _topic_thread_cache.get(chat_id)
    if cached:
        return cached

    stored_topic = None
    try:
        stored_topic = await backend_client.get_telegram_topic(chat_id)
    except httpx.HTTPError:
        stored_topic = None

    if stored_topic is not None:
        thread_id = stored_topic.get("telegram_thread_id")
        if thread_id is not None:
            _topic_thread_cache[chat_id] = thread_id
            return thread_id

    logger = logging.getLogger(__name__)
    # log chat info to help diagnose forum/topic creation issues
    try:
        chat_info = await bot.get_chat(chat_id)
        try:
            logger.info(
                "Chat info for %s: type=%s, title=%s, is_forum=%s",
                chat_id,
                getattr(chat_info, "type", None),
                getattr(chat_info, "title", None),
                getattr(chat_info, "is_forum", None),
            )
        except Exception:
            logger.info("Chat info for %s: %r", chat_id, chat_info)
    except Exception:
        logger.exception("Failed to get chat info for %s before creating forum topic", chat_id)

    try:
        topic = await bot.create_forum_topic(chat_id=chat_id, name=topic_name)
    except Exception:
        logger.exception("create_forum_topic failed for chat %s", chat_id)
        return None

    thread_id = getattr(topic, "message_thread_id", None)
    if thread_id is None:
        return None
    _topic_thread_cache[chat_id] = thread_id
    try:
        await backend_client.upsert_telegram_topic(chat_id, telegram_thread_id=thread_id)
    except httpx.HTTPError:
        logger.exception("Failed to save forum topic %s for chat %s", thread_id, chat_id)
    return thread_id


def _format_meetup_details(meetup: dict) -> str:
    date_label = escape(format_meetup_datetime(meetup["scheduled_at"]))
    participants = meetup.get("participants", [])
    participant_lines = [
        f"- {_format_participant_line(participant)}" for participant in participants
    ]
    if not participant_lines:
        participant_lines = ["- пока никто не подтвердил участие"]

    lines = [
        f"<b>Встреча #{meetup['id']}</b>",
        f"Дата: <code>{date_label}</code>",
        f"Игроков: {len(participants)}/{meetup['capacity_total']}",
    ]
    comment = meetup.get("comment")
    if comment:
        lines.append(f"Комментарий: {escape(comment)}")
    lines.extend(["", "Участники:", *participant_lines])
    return "\n".join(lines)


def _format_participant_line(participant: dict) -> str:
    username = participant.get("username")
    display_name = escape(participant.get("display_name", "Участник"))
    telegram_id = participant.get("telegram_id")
    if username:
        return f"@{escape(username)} (<code>{telegram_id}</code>)"
    return f"{display_name} (<code>{telegram_id}</code>)"


def _parse_meetup_id(callback_data: str | None, prefix: str) -> int | None:
    if callback_data is None:
        return None
    expected_prefix = f"{prefix}:"
    if not callback_data.startswith(expected_prefix):
        return None
    raw_value = callback_data[len(expected_prefix) :]
    if not raw_value.isdigit():
        return None
    return int(raw_value)


def _extract_error_detail(exc: httpx.HTTPStatusError) -> str:
    try:
        payload = exc.response.json()
    except ValueError:
        return exc.response.text
    detail = payload.get("detail", exc.response.text)
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    return str(detail)
