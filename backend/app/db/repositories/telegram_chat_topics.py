from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models.telegram_chat_topic import TelegramChatTopic


def get_telegram_chat_topic_by_chat_id(
    db: Session,
    telegram_chat_id: int,
) -> TelegramChatTopic | None:
    stmt = select(TelegramChatTopic).where(
        TelegramChatTopic.telegram_chat_id == telegram_chat_id,
    )
    return db.scalar(stmt)


def create_or_update_telegram_chat_topic(
    db: Session,
    telegram_chat_id: int,
    telegram_thread_id: int,
) -> TelegramChatTopic:
    topic = get_telegram_chat_topic_by_chat_id(db, telegram_chat_id)
    if topic is None:
        topic = TelegramChatTopic(
            telegram_chat_id=telegram_chat_id,
            telegram_thread_id=telegram_thread_id,
        )
        db.add(topic)
    else:
        topic.telegram_thread_id = telegram_thread_id
    db.commit()
    db.refresh(topic)
    return topic
