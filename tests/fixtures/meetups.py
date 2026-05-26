from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.db.models.meetup import Meetup
from backend.app.db.models.user import User
from backend.app.db.repositories import meetups as meetup_repository


def make_user(
    db: Session,
    *,
    telegram_id: int,
    display_name: str,
    username: str | None = None,
) -> User:
    user = User(
        telegram_id=telegram_id,
        display_name=display_name,
        username=username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_meetup(
    db: Session,
    creator: User,
    *,
    scheduled_at: datetime | None = None,
    capacity_total: int = 4,
    comment: str | None = "Test meetup",
    telegram_chat_id: int | None = None,
    telegram_thread_id: int | None = None,
) -> Meetup:
    return meetup_repository.create_meetup(
        db,
        creator_user_id=creator.id,
        scheduled_at=scheduled_at or datetime(2026, 6, 1, 18, 0, tzinfo=UTC),
        capacity_total=capacity_total,
        comment=comment,
        telegram_chat_id=telegram_chat_id,
        telegram_thread_id=telegram_thread_id,
    )
