from sqlalchemy.orm import Session

from backend.app.db.models.user import User
from backend.app.db.repositories import users as user_repository
from backend.app.schemas.user import UserTelegramSyncRequest


class BggUsernameAlreadyBoundError(ValueError):
    """Raised when a BGG username is already attached to another user."""


def _build_display_name(payload: UserTelegramSyncRequest) -> str:
    if payload.display_name:
        return payload.display_name.strip()

    full_name = " ".join(part for part in [payload.first_name, payload.last_name] if part).strip()
    if full_name:
        return full_name
    if payload.username:
        return f"@{payload.username}"
    return f"User {payload.telegram_id}"


def sync_telegram_user(db: Session, payload: UserTelegramSyncRequest) -> User:
    display_name = _build_display_name(payload)

    if payload.bgg_username:
        existing = user_repository.get_user_by_bgg_username(db, payload.bgg_username)
        if existing is not None and existing.telegram_id != payload.telegram_id:
            raise BggUsernameAlreadyBoundError(
                "This BGG username is already linked to another user."
            )

    return user_repository.upsert_user_by_telegram(db, payload, display_name)


def get_user(db: Session, user_id: int) -> User | None:
    return user_repository.get_user_by_id(db, user_id)


def get_user_by_telegram_id(db: Session, telegram_id: int) -> User | None:
    return user_repository.get_user_by_telegram_id(db, telegram_id)


def list_users_with_games(
    db: Session,
    *,
    exclude_user_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[User]:
    return user_repository.list_users_with_games(
        db,
        exclude_user_id=exclude_user_id,
        limit=limit,
        offset=offset,
    )
