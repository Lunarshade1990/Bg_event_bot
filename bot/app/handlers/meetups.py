from html import escape

import httpx
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from backend.app.core.config import get_settings
from bot.app.keyboards.main_menu import get_main_menu_keyboard
from bot.app.keyboards.meetups import (
    MEETUP_CALLBACK_PREFIX,
    MEETUP_DELETE_CALLBACK_PREFIX,
    MEETUP_DELETE_CONFIRM_CALLBACK_PREFIX,
    MEETUP_JOIN_CALLBACK_PREFIX,
    MEETUP_LEAVE_CALLBACK_PREFIX,
    get_meetup_delete_confirm_keyboard,
    get_meetup_detail_keyboard,
    get_group_meetup_keyboard,
    get_meetups_list_keyboard,
    get_meetups_menu_keyboard,
)
from bot.app.services.backend_api import BackendAPIClient
from bot.app.states.create_meetup import CreateMeetupStates
from bot.app.utils.meetup_datetime import (
    MEETUP_DATETIME_EXAMPLE,
    format_meetup_datetime,
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
    await state.set_state(CreateMeetupStates.waiting_for_date)
    await message.answer(
        "Создание встречи.\n"
        "Укажи дату и время в формате "
        f"<code>{MEETUP_DATETIME_EXAMPLE}</code> (UTC).",
        parse_mode="HTML",
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
    await _ensure_forum_topic_thread_id(
        bot=bot,
        chat_id=chat.id,
        topic_name=topic_name,
        backend_client=backend_client,
    )


@router.message(F.text == "Назад")
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())


@router.message(F.text == "Создать встречу")
async def start_create_meetup(message: Message, state: FSMContext) -> None:
    if not await _ensure_profile(message):
        return

    await state.set_state(CreateMeetupStates.waiting_for_date)
    await message.answer(
        "Укажи дату и время встречи в формате "
        f"<code>{MEETUP_DATETIME_EXAMPLE}</code> (UTC).",
        parse_mode="HTML",
    )


@router.message(CreateMeetupStates.waiting_for_date)
async def receive_meetup_date(message: Message, state: FSMContext) -> None:
    parsed = parse_meetup_datetime(message.text or "")
    if parsed is None:
        await message.answer(
            "Не удалось разобрать дату. Пример: "
            f"<code>{MEETUP_DATETIME_EXAMPLE}</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(scheduled_at=parsed.isoformat())
    await state.set_state(CreateMeetupStates.waiting_for_capacity)
    await message.answer("Сколько всего игроков может участвовать? (число от 1)")


@router.message(CreateMeetupStates.waiting_for_capacity)
async def receive_meetup_capacity(message: Message, state: FSMContext) -> None:
    raw_value = (message.text or "").strip()
    if not raw_value.isdigit():
        await message.answer("Нужно целое число, например: 4")
        return

    capacity_total = int(raw_value)
    if capacity_total < 1:
        await message.answer("Вместимость должна быть не меньше 1.")
        return

    await state.update_data(capacity_total=capacity_total)
    await state.set_state(CreateMeetupStates.waiting_for_comment)
    await message.answer(
        "Добавь комментарий к встрече или отправь <code>-</code>, чтобы пропустить.",
        parse_mode="HTML",
    )


@router.message(CreateMeetupStates.waiting_for_comment)
async def receive_meetup_comment(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

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

    backend_client = BackendAPIClient()
    profile = await _ensure_profile_for_user(message, backend_client=backend_client)
    if profile is None:
        return

    try:
        telegram_chat_id = data.get("telegram_chat_id")
        telegram_thread_id = data.get("telegram_thread_id")
        meetup = await backend_client.create_meetup(
            creator_user_id=profile["id"],
            scheduled_at=scheduled_at,
            capacity_total=capacity_total,
            comment=comment,
            telegram_chat_id=telegram_chat_id,
            telegram_thread_id=telegram_thread_id,
        )
    except httpx.HTTPStatusError as exc:
        await message.answer(f"Не удалось создать встречу: {_extract_error_detail(exc)}")
        return
    except httpx.HTTPError:
        await message.answer("Не удалось связаться с backend API.")
        return

    await state.clear()
    if telegram_chat_id and telegram_thread_id:
        sent = await message.bot.send_message(
            chat_id=telegram_chat_id,
            message_thread_id=telegram_thread_id,
            text=_format_group_meetup_card(meetup),
            parse_mode="HTML",
            reply_markup=_build_group_keyboard_for_user(meetup, telegram_id=user.id),
        )
        try:
            await backend_client.set_meetup_telegram_message_id(
                meetup["id"],
                telegram_message_id=sent.message_id,
            )
        except httpx.HTTPError:
            pass

        await message.answer("Встреча создана и опубликована в теме.", reply_markup=get_main_menu_keyboard())
        return

    await message.answer(_format_meetup_details(meetup), parse_mode="HTML", reply_markup=get_meetups_menu_keyboard())


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

    await _send_meetups_list(message, edit_message=True)
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

    user = callback.from_user
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

    user = callback.from_user
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

    await message.edit_text(
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
        await message.edit_text("Встреча удалена.")
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
        await message.edit_text(
            _format_group_meetup_card(meetup),
            parse_mode="HTML",
            reply_markup=_build_group_keyboard_for_user(meetup, telegram_id=user.id),
        )
    else:
        joined_user_ids = {participant["telegram_id"] for participant in meetup["participants"]}
        can_join = user.id not in joined_user_ids and len(meetup["participants"]) < meetup["capacity_total"]
        await message.edit_text(
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

    comment = meetup.get("comment")
    comment_line = escape(comment) if comment else "без комментария"

    return "\n".join(
        [
            f"<b>Встреча</b> (#{meetup['id']})",
            f"Дата: <code>{date_label}</code>",
            f"Свободно мест: <b>{free}</b> из {capacity}",
            f"Комментарий: {comment_line}",
            "",
            "<b>Участники:</b>",
            *participant_lines,
        ]
    )


async def _ensure_profile_for_user(message: Message, *, backend_client: BackendAPIClient) -> dict | None:
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

    try:
        topic = await bot.create_forum_topic(chat_id=chat_id, name=topic_name)
    except Exception:
        return None

    thread_id = getattr(topic, "message_thread_id", None)
    if thread_id is None:
        return None
    _topic_thread_cache[chat_id] = thread_id
    try:
        await backend_client.upsert_telegram_topic(chat_id, telegram_thread_id=thread_id)
    except httpx.HTTPError:
        pass
    return thread_id

def _format_meetup_details(meetup: dict) -> str:
    date_label = escape(format_meetup_datetime(meetup["scheduled_at"]))
    participants = meetup.get("participants", [])
    participant_lines = [
        f"- {_format_participant_line(participant)}" for participant in participants
    ]
    if not participant_lines:
        participant_lines = ["- пока никто не подтвердил участие"]

    comment = meetup.get("comment")
    comment_line = escape(comment) if comment else "без комментария"

    return "\n".join(
        [
            f"<b>Встреча #{meetup['id']}</b>",
            f"Дата: <code>{date_label}</code>",
            f"Игроков: {len(participants)}/{meetup['capacity_total']}",
            f"Комментарий: {comment_line}",
            "",
            "Участники:",
            *participant_lines,
        ]
    )


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
