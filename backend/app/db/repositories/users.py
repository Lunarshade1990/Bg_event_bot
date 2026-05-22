from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models.user import User
from backend.app.schemas.user import UserTelegramSyncRequest


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_telegram_id(db: Session, telegram_id: int) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    return db.scalar(stmt)


def get_user_by_bgg_username(db: Session, bgg_username: str) -> User | None:
    stmt = select(User).where(User.bgg_username == bgg_username)
    return db.scalar(stmt)


def upsert_user_by_telegram(db: Session, payload: UserTelegramSyncRequest, display_name: str) -> User:
    user = get_user_by_telegram_id(db, payload.telegram_id)

    if user is None:
        user = User(
            telegram_id=payload.telegram_id,
            username=payload.username,
            first_name=payload.first_name,
            last_name=payload.last_name,
            display_name=display_name,
            bgg_username=payload.bgg_username,
        )
        db.add(user)
    else:
        user.username = payload.username
        user.first_name = payload.first_name
        user.last_name = payload.last_name
        user.display_name = display_name
        user.bgg_username = payload.bgg_username

    db.commit()
    db.refresh(user)
    return user
