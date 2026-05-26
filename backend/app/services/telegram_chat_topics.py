from sqlalchemy.orm import Session

from backend.app.db.repositories import telegram_chat_topics as telegram_chat_topics_repository
from backend.app.schemas.telegram_chat_topic import (
    TelegramChatTopicCreateRequest,
    TelegramChatTopicRead,
)


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
    )
    return TelegramChatTopicRead.model_validate(topic)
