from sqlalchemy.orm import Session

from backend.app.db.repositories import telegram_chat_topics as telegram_chat_topics_repository
from backend.app.db.repositories import users as user_repository
from backend.app.schemas.telegram_chat_topic import (
    TelegramChatMembershipCreateRequest,
    TelegramChatTopicCreateRequest,
    TelegramChatTopicRead,
)


class TelegramChatMembershipUserNotFoundError(ValueError):
    """Raised when a chat membership references an unknown user."""


def get_telegram_chat_topic(db: Session, telegram_chat_id: int) -> TelegramChatTopicRead | None:
    topic = telegram_chat_topics_repository.get_telegram_chat_topic_by_chat_id(db, telegram_chat_id)
    if topic is None:
        return None
    return TelegramChatTopicRead.model_validate(topic)


def upsert_telegram_chat_topic(
    db: Session,
    payload: TelegramChatTopicCreateRequest,
) -> TelegramChatTopicRead:
    topic = telegram_chat_topics_repository.create_or_update_telegram_chat_topic(
        db,
        telegram_chat_id=payload.telegram_chat_id,
        telegram_thread_id=payload.telegram_thread_id,
        title=payload.title,
    )
    return TelegramChatTopicRead.model_validate(topic)


def register_telegram_chat_membership(
    db: Session,
    payload: TelegramChatMembershipCreateRequest,
) -> TelegramChatTopicRead:
    user = user_repository.get_user_by_id(db, payload.user_id)
    if user is None:
        raise TelegramChatMembershipUserNotFoundError("User not found.")

    topic = telegram_chat_topics_repository.create_or_update_telegram_chat_topic(
        db,
        telegram_chat_id=payload.telegram_chat_id,
        telegram_thread_id=payload.telegram_thread_id,
        title=payload.title,
    )
    telegram_chat_topics_repository.add_user_to_telegram_chat(
        db,
        telegram_chat_id=payload.telegram_chat_id,
        user_id=payload.user_id,
    )
    return TelegramChatTopicRead.model_validate(topic)


def list_telegram_chat_topics_for_user(db: Session, user_id: int) -> list[TelegramChatTopicRead]:
    return [
        TelegramChatTopicRead.model_validate(topic)
        for topic in telegram_chat_topics_repository.list_telegram_chat_topics_for_user(db, user_id)
    ]
