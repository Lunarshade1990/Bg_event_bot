from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models.enums import MeetupStatus, ParticipantStatus
from backend.app.db.models.meetup import Meetup
from backend.app.db.models.meetup_game import MeetupGame
from backend.app.db.models.meetup_game_suggestion import MeetupGameSuggestion
from backend.app.db.models.meetup_game_vote import MeetupGameVote
from backend.app.db.models.meetup_participant import MeetupParticipant
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


def _meetup_load_options():
    return (
        selectinload(Meetup.participants).selectinload(MeetupParticipant.user),
        selectinload(Meetup.creator).selectinload(User.user_games).selectinload(UserGame.game),
        selectinload(Meetup.participants)
        .selectinload(MeetupParticipant.user)
        .selectinload(User.user_games)
        .selectinload(UserGame.game),
        selectinload(Meetup.meetup_games).selectinload(MeetupGame.game),
        selectinload(Meetup.game_suggestions).selectinload(MeetupGameSuggestion.proposer),
        selectinload(Meetup.game_suggestions).selectinload(MeetupGameSuggestion.game),
        selectinload(Meetup.game_votes).selectinload(MeetupGameVote.user),
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
    game_ids: list[int] | None = None,
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

    for game_id in dict.fromkeys(game_ids or []):
        db.add(
            MeetupGame(
                meetup_id=meetup.id,
                game_id=game_id,
                added_by_user_id=creator_user_id,
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


def get_meetup_for_update(db: Session, meetup_id: int) -> Meetup | None:
    return db.scalar(select(Meetup).where(Meetup.id == meetup_id).with_for_update())


def update_meetup(
    db: Session,
    meetup: Meetup,
    *,
    fields: dict,
    game_ids: list[int] | None = None,
) -> Meetup:
    for field, value in fields.items():
        setattr(meetup, field, value)

    if game_ids is not None:
        db.query(MeetupGame).filter(MeetupGame.meetup_id == meetup.id).delete(
            synchronize_session=False
        )
        db.add_all(
            MeetupGame(
                meetup_id=meetup.id,
                game_id=game_id,
                added_by_user_id=meetup.creator_user_id,
            )
            for game_id in dict.fromkeys(game_ids)
        )

    db.commit()
    loaded = get_meetup_by_id(db, meetup.id)
    if loaded is None:
        raise RuntimeError("Meetup was updated but could not be loaded.")
    return loaded


def list_meetups(
    db: Session,
    *,
    archive: bool = False,
    telegram_chat_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Meetup]:
    stmt = select(Meetup)
    now = datetime.now(UTC)
    if archive:
        stmt = stmt.where(Meetup.scheduled_at < now)
    else:
        stmt = stmt.where(Meetup.scheduled_at >= now)
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


def replace_game_suggestions(
    db: Session,
    *,
    meetup_id: int,
    proposer_user_id: int,
    collection_owner_user_id: int,
    game_ids: list[int],
) -> None:
    db.scalar(select(Meetup.id).where(Meetup.id == meetup_id).with_for_update())
    db.query(MeetupGameSuggestion).filter(
        MeetupGameSuggestion.meetup_id == meetup_id,
        MeetupGameSuggestion.proposer_user_id == proposer_user_id,
    ).delete(synchronize_session=False)
    db.add_all(
        MeetupGameSuggestion(
            meetup_id=meetup_id,
            proposer_user_id=proposer_user_id,
            collection_owner_user_id=collection_owner_user_id,
            game_id=game_id,
        )
        for game_id in game_ids
    )
    db.flush()
    remaining_game_ids = select(MeetupGameSuggestion.game_id).where(
        MeetupGameSuggestion.meetup_id == meetup_id
    )
    db.query(MeetupGameVote).filter(
        MeetupGameVote.meetup_id == meetup_id,
        ~MeetupGameVote.game_id.in_(remaining_game_ids),
    ).delete(synchronize_session=False)
    db.commit()


def has_suggested_game(db: Session, *, meetup_id: int, game_id: int) -> bool:
    stmt = (
        select(MeetupGameSuggestion.id)
        .where(
            MeetupGameSuggestion.meetup_id == meetup_id,
            MeetupGameSuggestion.game_id == game_id,
        )
        .limit(1)
    )
    return db.scalar(stmt) is not None


def toggle_game_vote(
    db: Session,
    *,
    meetup_id: int,
    game_id: int,
    user_id: int,
) -> bool:
    db.scalar(select(Meetup.id).where(Meetup.id == meetup_id).with_for_update())
    existing = db.scalar(
        select(MeetupGameVote).where(
            MeetupGameVote.meetup_id == meetup_id,
            MeetupGameVote.game_id == game_id,
            MeetupGameVote.user_id == user_id,
        )
    )
    if existing is None:
        db.add(MeetupGameVote(meetup_id=meetup_id, game_id=game_id, user_id=user_id))
        voted = True
    else:
        db.delete(existing)
        voted = False
    db.commit()
    return voted


def delete_meetup(db: Session, meetup: Meetup) -> None:
    db.delete(meetup)
    db.commit()
