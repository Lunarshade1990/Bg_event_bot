from sqlalchemy.orm import Session

from backend.app.db.models.enums import MeetupStatus, ParticipantStatus
from backend.app.db.models.meetup import Meetup
from backend.app.db.repositories import meetups as meetup_repository
from backend.app.db.repositories import users as user_repository
from backend.app.schemas.meetup import (
    MeetupCreateRequest,
    MeetupParticipantRead,
    MeetupRead,
)


class MeetupNotFoundError(ValueError):
    """Raised when a meetup does not exist."""


class MeetupForbiddenError(ValueError):
    """Raised when a user is not allowed to perform an action on a meetup."""


class MeetupCapacityFullError(ValueError):
    """Raised when a meetup has no free participant slots."""


class MeetupNotJoinableError(ValueError):
    """Raised when a meetup cannot accept new participants."""


class MeetupAlreadyJoinedError(ValueError):
    """Raised when a user is already a joined participant."""


def _build_meetup_read(meetup: Meetup) -> MeetupRead:
    participants = [
        MeetupParticipantRead(
            telegram_id=participant.user.telegram_id,
            display_name=participant.user.display_name,
            username=participant.user.username,
            status=participant.status,
        )
        for participant in meetup.participants
        if participant.status == ParticipantStatus.JOINED
    ]
    return MeetupRead(
        id=meetup.id,
        scheduled_at=meetup.scheduled_at,
        capacity_total=meetup.capacity_total,
        comment=meetup.comment,
        status=meetup.status,
        creator_user_id=meetup.creator_user_id,
        telegram_chat_id=meetup.telegram_chat_id,
        telegram_thread_id=meetup.telegram_thread_id,
        telegram_message_id=meetup.telegram_message_id,
        participants=participants,
    )


def create_meetup(db: Session, payload: MeetupCreateRequest) -> MeetupRead:
    creator = user_repository.get_user_by_id(db, payload.creator_user_id)
    if creator is None:
        raise MeetupNotFoundError("Creator user not found.")

    meetup = meetup_repository.create_meetup(
        db,
        creator_user_id=payload.creator_user_id,
        scheduled_at=payload.scheduled_at,
        capacity_total=payload.capacity_total,
        comment=payload.comment,
        telegram_chat_id=payload.telegram_chat_id,
        telegram_thread_id=payload.telegram_thread_id,
        title=None,
        location="",
    )
    return _build_meetup_read(meetup)


def get_meetup(db: Session, meetup_id: int) -> MeetupRead | None:
    meetup = meetup_repository.get_meetup_by_id(db, meetup_id)
    if meetup is None:
        return None
    return _build_meetup_read(meetup)


def list_meetups(
    db: Session,
    *,
    telegram_chat_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[MeetupRead]:
    meetups = meetup_repository.list_meetups(
        db,
        telegram_chat_id=telegram_chat_id,
        limit=limit,
        offset=offset,
    )
    return [_build_meetup_read(meetup) for meetup in meetups]


def join_meetup(db: Session, meetup_id: int, user_id: int) -> MeetupRead:
    meetup = meetup_repository.get_meetup_by_id(db, meetup_id)
    if meetup is None:
        raise MeetupNotFoundError("Meetup not found.")

    if meetup.status != MeetupStatus.PLANNED:
        raise MeetupNotJoinableError("Meetup is not open for joining.")

    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise MeetupNotFoundError("User not found.")

    existing = meetup_repository.get_participant(db, meetup_id, user_id)
    if existing is not None and existing.status == ParticipantStatus.JOINED:
        raise MeetupAlreadyJoinedError("User has already joined this meetup.")

    joined_count = meetup_repository.count_joined_participants(db, meetup_id)
    if joined_count >= meetup.capacity_total:
        raise MeetupCapacityFullError("Meetup is full.")

    meetup_repository.add_participant(db, meetup_id, user_id)

    refreshed = meetup_repository.get_meetup_by_id(db, meetup_id)
    if refreshed is None:
        raise MeetupNotFoundError("Meetup not found.")
    return _build_meetup_read(refreshed)


def leave_meetup(db: Session, meetup_id: int, user_id: int) -> MeetupRead:
    meetup = meetup_repository.get_meetup_by_id(db, meetup_id)
    if meetup is None:
        raise MeetupNotFoundError("Meetup not found.")

    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise MeetupNotFoundError("User not found.")

    participant = meetup_repository.get_participant(db, meetup_id, user_id)
    if participant is not None and participant.status == ParticipantStatus.JOINED:
        meetup_repository.set_participant_status(
            db,
            meetup_id=meetup_id,
            user_id=user_id,
            status=ParticipantStatus.CANCELLED,
        )

    refreshed = meetup_repository.get_meetup_by_id(db, meetup_id)
    if refreshed is None:
        raise MeetupNotFoundError("Meetup not found.")
    return _build_meetup_read(refreshed)


def set_telegram_message_id(db: Session, meetup_id: int, telegram_message_id: int) -> MeetupRead:
    meetup = meetup_repository.set_meetup_telegram_message_id(
        db,
        meetup_id=meetup_id,
        telegram_message_id=telegram_message_id,
    )
    if meetup is None:
        raise MeetupNotFoundError("Meetup not found.")
    refreshed = meetup_repository.get_meetup_by_id(db, meetup_id)
    if refreshed is None:
        raise MeetupNotFoundError("Meetup not found.")
    return _build_meetup_read(refreshed)


def delete_meetup(db: Session, meetup_id: int, requesting_user_id: int) -> None:
    meetup = meetup_repository.get_meetup_by_id(db, meetup_id, load_participants=False)
    if meetup is None:
        raise MeetupNotFoundError("Meetup not found.")

    if meetup.creator_user_id != requesting_user_id:
        raise MeetupForbiddenError("Only the meetup creator can delete it.")

    meetup_repository.delete_meetup(db, meetup)
