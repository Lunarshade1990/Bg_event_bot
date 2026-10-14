from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from aiogram import Bot
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.methods import (
    EditEphemeralMessageCaption,
    EditEphemeralMessageMedia,
    EditEphemeralMessageReplyMarkup,
    EditEphemeralMessageText,
    EditMessageCaption,
    EditMessageMedia,
    EditMessageReplyMarkup,
    EditMessageText,
)
from aiogram.methods.base import TelegramMethod
from aiogram.types import EphemeralMessageParameters, Message, Update


@dataclass(frozen=True)
class EphemeralReplyContext:
    chat_id: int
    receiver_user_id: int
    callback_query_id: str | None = None
    ephemeral_message_id: int | None = None


_current_context: ContextVar[EphemeralReplyContext | None] = ContextVar(
    "ephemeral_reply_context",
    default=None,
)
_persistent_message: ContextVar[bool] = ContextVar("persistent_group_message", default=False)


class EphemeralReplyContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        context = _get_ephemeral_context(event)
        token = _current_context.set(context)
        try:
            return await handler(event, data)
        finally:
            _current_context.reset(token)


async def ephemeral_request_middleware(
    make_request: Callable[[Bot, TelegramMethod[Any]], Awaitable[Any]],
    bot: Bot,
    method: TelegramMethod[Any],
) -> Any:
    context = _current_context.get()
    if context is None or _persistent_message.get():
        return await make_request(bot, method)

    if context.ephemeral_message_id is not None and _matches_chat(method, context.chat_id):
        method = _edit_ephemeral_message(method, context)

    if (
        _matches_chat(method, context.chat_id)
        and "ephemeral_message_parameters" in type(method).model_fields
        and getattr(method, "ephemeral_message_parameters", None) is None
    ):
        method = method.model_copy(
            update={
                "ephemeral_message_parameters": EphemeralMessageParameters(
                    receiver_user_id=context.receiver_user_id,
                    callback_query_id=context.callback_query_id,
                )
            }
        )

    return await make_request(bot, method)


@contextmanager
def persistent_group_message() -> Iterator[None]:
    token: Token[bool] = _persistent_message.set(True)
    try:
        yield
    finally:
        _persistent_message.reset(token)


def _get_ephemeral_context(event: Update) -> EphemeralReplyContext | None:
    callback = event.callback_query
    if callback is not None:
        message = callback.message
        if isinstance(message, Message) and message.chat.type in {"group", "supergroup"}:
            return EphemeralReplyContext(
                chat_id=message.chat.id,
                receiver_user_id=callback.from_user.id,
                callback_query_id=callback.id,
                ephemeral_message_id=message.ephemeral_message_id,
            )
        return None

    message = event.message
    if (
        message is None
        or message.from_user is None
        or message.chat.type not in {"group", "supergroup"}
    ):
        return None

    return EphemeralReplyContext(
        chat_id=message.chat.id,
        receiver_user_id=message.from_user.id,
    )


def _matches_chat(method: TelegramMethod[Any], chat_id: int) -> bool:
    method_chat_id = getattr(method, "chat_id", None)
    return method_chat_id is not None and str(method_chat_id) == str(chat_id)


def _edit_ephemeral_message(
    method: TelegramMethod[Any],
    context: EphemeralReplyContext,
) -> TelegramMethod[Any]:
    chat_id = context.chat_id
    receiver_user_id = context.receiver_user_id
    ephemeral_message_id = context.ephemeral_message_id
    assert ephemeral_message_id is not None

    if isinstance(method, EditMessageText):
        return EditEphemeralMessageText(
            chat_id=chat_id,
            receiver_user_id=receiver_user_id,
            ephemeral_message_id=ephemeral_message_id,
            text=method.text,
            parse_mode=method.parse_mode,
            entities=method.entities,
            link_preview_options=method.link_preview_options,
            reply_markup=method.reply_markup,
            rich_message=method.rich_message,
        )
    if isinstance(method, EditMessageCaption):
        return EditEphemeralMessageCaption(
            chat_id=chat_id,
            receiver_user_id=receiver_user_id,
            ephemeral_message_id=ephemeral_message_id,
            caption=method.caption,
            parse_mode=method.parse_mode,
            caption_entities=method.caption_entities,
            reply_markup=method.reply_markup,
            show_caption_above_media=method.show_caption_above_media,
        )
    if isinstance(method, EditMessageMedia):
        return EditEphemeralMessageMedia(
            chat_id=chat_id,
            receiver_user_id=receiver_user_id,
            ephemeral_message_id=ephemeral_message_id,
            media=method.media,
            reply_markup=method.reply_markup,
        )
    if isinstance(method, EditMessageReplyMarkup):
        return EditEphemeralMessageReplyMarkup(
            chat_id=chat_id,
            receiver_user_id=receiver_user_id,
            ephemeral_message_id=ephemeral_message_id,
            reply_markup=method.reply_markup,
        )
    return method
