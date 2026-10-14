from datetime import UTC, datetime

import pytest
from aiogram import Bot
from aiogram.methods import (
    EditEphemeralMessageText,
    EditMessageText,
    SendMessage,
    SendRichMessage,
)
from aiogram.types import (
    CallbackQuery,
    Chat,
    EphemeralMessageParameters,
    InputRichBlockParagraph,
    InputRichMessage,
    Message,
    Update,
    User,
)

from bot.app.middlewares.ephemeral_replies import (
    EphemeralReplyContextMiddleware,
    ephemeral_request_middleware,
    persistent_group_message,
)


@pytest.fixture
def user() -> User:
    return User(id=77, is_bot=False, first_name="Ada")


def _group_message(user: User, *, ephemeral_message_id: int | None = None) -> Message:
    return Message(
        message_id=51,
        date=datetime.now(UTC),
        chat=Chat(id=-100123, type="supergroup"),
        from_user=user,
        ephemeral_message_id=ephemeral_message_id,
    )


async def _send_during_update(
    update: Update,
    outgoing_method,
    *,
    persistent: bool = False,
):
    bot = Bot(token="123456:TEST")
    captured_methods = []

    async def make_request(_bot, method):
        captured_methods.append(method)
        return method

    async def handler(_event, _data):
        if persistent:
            with persistent_group_message():
                await ephemeral_request_middleware(make_request, bot, outgoing_method)
        else:
            await ephemeral_request_middleware(make_request, bot, outgoing_method)

    try:
        await EphemeralReplyContextMiddleware()(handler, update, {})
    finally:
        await bot.session.close()
    return captured_methods[0]


@pytest.mark.asyncio
async def test_group_message_answers_ephemerally_to_the_sender(user: User) -> None:
    update = Update(
        update_id=1,
        message=_group_message(user),
    )

    sent = await _send_during_update(
        update,
        SendMessage(chat_id=-100123, text="Reply"),
    )

    assert sent.ephemeral_message_parameters == EphemeralMessageParameters(
        receiver_user_id=user.id,
    )


@pytest.mark.asyncio
async def test_private_chat_message_is_not_made_ephemeral(user: User) -> None:
    update = Update(
        update_id=1,
        message=Message(
            message_id=51,
            date=datetime.now(UTC),
            chat=Chat(id=user.id, type="private"),
            from_user=user,
        ),
    )

    sent = await _send_during_update(
        update,
        SendMessage(chat_id=user.id, text="Reply"),
    )

    assert sent.ephemeral_message_parameters is None


@pytest.mark.asyncio
async def test_group_callback_answers_use_callback_and_recipient_ids(user: User) -> None:
    update = Update(
        update_id=1,
        callback_query=CallbackQuery(
            id="callback-query",
            from_user=user,
            chat_instance="chat-instance",
            message=_group_message(user),
        ),
    )

    sent = await _send_during_update(
        update,
        SendMessage(chat_id=-100123, text="Reply"),
    )

    assert sent.ephemeral_message_parameters == EphemeralMessageParameters(
        receiver_user_id=user.id,
        callback_query_id="callback-query",
    )


@pytest.mark.asyncio
async def test_group_response_sent_to_private_chat_is_not_made_ephemeral(user: User) -> None:
    update = Update(
        update_id=1,
        message=_group_message(user),
    )

    sent = await _send_during_update(
        update,
        SendMessage(chat_id=user.id, text="Private reply"),
    )

    assert sent.ephemeral_message_parameters is None


@pytest.mark.asyncio
async def test_group_rich_message_is_ephemeral(user: User) -> None:
    update = Update(
        update_id=1,
        message=_group_message(user),
    )

    sent = await _send_during_update(
        update,
        SendRichMessage(
            chat_id=-100123,
            rich_message=InputRichMessage(
                blocks=[InputRichBlockParagraph(text="Rich reply")],
            ),
        ),
    )

    assert sent.ephemeral_message_parameters == EphemeralMessageParameters(
        receiver_user_id=user.id,
    )


@pytest.mark.asyncio
async def test_ephemeral_callback_edits_its_ephemeral_message(user: User) -> None:
    update = Update(
        update_id=1,
        callback_query=CallbackQuery(
            id="callback-query",
            from_user=user,
            chat_instance="chat-instance",
            message=_group_message(user, ephemeral_message_id=987),
        ),
    )

    edited = await _send_during_update(
        update,
        EditMessageText(chat_id=-100123, message_id=51, text="Updated"),
    )

    assert isinstance(edited, EditEphemeralMessageText)
    assert edited.chat_id == -100123
    assert edited.receiver_user_id == user.id
    assert edited.ephemeral_message_id == 987
    assert edited.text == "Updated"


@pytest.mark.asyncio
async def test_persistent_meetup_card_is_not_made_ephemeral(user: User) -> None:
    update = Update(
        update_id=1,
        callback_query=CallbackQuery(
            id="callback-query",
            from_user=user,
            chat_instance="chat-instance",
            message=_group_message(user),
        ),
    )

    sent = await _send_during_update(
        update,
        SendRichMessage(
            chat_id=-100123,
            rich_message=InputRichMessage(
                blocks=[InputRichBlockParagraph(text="Meetup card")],
            ),
        ),
        persistent=True,
    )

    assert sent.ephemeral_message_parameters is None


@pytest.mark.asyncio
async def test_callback_on_regular_group_message_keeps_regular_edit(user: User) -> None:
    update = Update(
        update_id=1,
        callback_query=CallbackQuery(
            id="callback-query",
            from_user=user,
            chat_instance="chat-instance",
            message=_group_message(user),
        ),
    )

    edited = await _send_during_update(
        update,
        EditMessageText(chat_id=-100123, message_id=51, text="Updated"),
    )

    assert isinstance(edited, EditMessageText)
