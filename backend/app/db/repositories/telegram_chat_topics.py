from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models.telegram_chat_member import TelegramChatMember
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
    title: str | None = None,
) -> TelegramChatTopic:
    topic = get_telegram_chat_topic_by_chat_id(db, telegram_chat_id)
    if topic is None:
        topic = TelegramChatTopic(
            telegram_chat_id=telegram_chat_id,
            telegram_thread_id=telegram_thread_id,
            title=title,
        )
        db.add(topic)
    else:
        topic.telegram_thread_id = telegram_thread_id
        if title is not None:
            topic.title = title
    db.commit()
    db.refresh(topic)
    return topic


def add_user_to_telegram_chat(
    db: Session,
    *,
    telegram_chat_id: int,
    user_id: int,
) -> TelegramChatMember:
    stmt = select(TelegramChatMember).where(
        TelegramChatMember.telegram_chat_id == telegram_chat_id,
        TelegramChatMember.user_id == user_id,
    )
    member = db.scalar(stmt)
    if member is None:
        member = TelegramChatMember(telegram_chat_id=telegram_chat_id, user_id=user_id)
        db.add(member)
        db.commit()
        db.refresh(member)
    return member


def list_telegram_chat_topics_for_user(db: Session, user_id: int) -> list[TelegramChatTopic]:
    stmt = (
        select(TelegramChatTopic)
        .join(TelegramChatMember, TelegramChatMember.telegram_chat_id == TelegramChatTopic.telegram_chat_id)
        .where(TelegramChatMember.user_id == user_id)
        .options(selectinload(TelegramChatTopic.members))
        .order_by(TelegramChatTopic.title.asc().nulls_last(), TelegramChatTopic.telegram_chat_id.asc())
    )
    return list(db.scalars(stmt).all())
