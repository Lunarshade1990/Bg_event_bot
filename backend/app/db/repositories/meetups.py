from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models.enums import MeetupStatus, ParticipantStatus
from backend.app.db.models.meetup import Meetup
from backend.app.db.models.meetup_participant import MeetupParticipant


def _meetup_load_options():
    return (
        selectinload(Meetup.participants).selectinload(MeetupParticipant.user),
    )


def create_meetup(
    db: Session,
    *,
    creator_user_id: int,
    scheduled_at: datetime,
    capacity_total: int,
    comment: str | None = None,
    telegram_chat_id: int | None = None,
    telegram_thread_id: int | None = None,
    telegram_message_id: int | None = None,
    title: str | None = None,
    location: str = "",
) -> Meetup:
    meetup = Meetup(
        creator_user_id=creator_user_id,
        title=title,
        scheduled_at=scheduled_at,
        location=location,
        comment=comment,
        capacity_total=capacity_total,
        telegram_chat_id=telegram_chat_id,
        telegram_thread_id=telegram_thread_id,
        telegram_message_id=telegram_message_id,
        status=MeetupStatus.PLANNED,
    )
    db.add(meetup)
    db.flush()

    db.add(
        MeetupParticipant(
            meetup_id=meetup.id,
            user_id=creator_user_id,
            status=ParticipantStatus.JOINED,
        )
    )
    db.commit()

    loaded = get_meetup_by_id(db, meetup.id)
    if loaded is None:
        raise RuntimeError("Meetup was created but could not be loaded.")
    return loaded


def get_meetup_by_id(db: Session, meetup_id: int, *, load_participants: bool = True) -> Meetup | None:
    stmt = select(Meetup).where(Meetup.id == meetup_id)
    if load_participants:
        stmt = stmt.options(*_meetup_load_options())
    return db.scalar(stmt)


def list_meetups(
    db: Session,
    *,
    status: MeetupStatus = MeetupStatus.PLANNED,
    telegram_chat_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Meetup]:
    stmt = select(Meetup).where(Meetup.status == status)
    if telegram_chat_id is not None:
        stmt = stmt.where(Meetup.telegram_chat_id == telegram_chat_id)
    stmt = (
        stmt.options(*_meetup_load_options())
        .order_by(Meetup.scheduled_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


def count_joined_participants(db: Session, meetup_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(MeetupParticipant)
        .where(
            MeetupParticipant.meetup_id == meetup_id,
            MeetupParticipant.status == ParticipantStatus.JOINED,
        )
    )
    return int(db.scalar(stmt) or 0)


def get_participant(db: Session, meetup_id: int, user_id: int) -> MeetupParticipant | None:
    stmt = select(MeetupParticipant).where(
        MeetupParticipant.meetup_id == meetup_id,
        MeetupParticipant.user_id == user_id,
    )
    return db.scalar(stmt)


def add_participant(db: Session, meetup_id: int, user_id: int) -> MeetupParticipant:
    existing = get_participant(db, meetup_id, user_id)
    if existing is not None:
        if existing.status == ParticipantStatus.JOINED:
            return existing
        existing.status = ParticipantStatus.JOINED
        db.commit()
        db.refresh(existing)
        return existing

    participant = MeetupParticipant(
        meetup_id=meetup_id,
        user_id=user_id,
        status=ParticipantStatus.JOINED,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def set_participant_status(
    db: Session,
    *,
    meetup_id: int,
    user_id: int,
    status: ParticipantStatus,
) -> MeetupParticipant | None:
    participant = get_participant(db, meetup_id, user_id)
    if participant is None:
        return None
    participant.status = status
    db.commit()
    db.refresh(participant)
    return participant


def set_meetup_telegram_message_id(
    db: Session,
    *,
    meetup_id: int,
    telegram_message_id: int,
) -> Meetup | None:
    meetup = get_meetup_by_id(db, meetup_id, load_participants=False)
    if meetup is None:
        return None
    meetup.telegram_message_id = telegram_message_id
    db.commit()
    db.refresh(meetup)
    return meetup


def delete_meetup(db: Session, meetup: Meetup) -> None:
    db.delete(meetup)
    db.commit()
