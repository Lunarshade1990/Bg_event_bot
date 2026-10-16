from sqlalchemy.orm import Session

from backend.app.db.models.enums import GameType, MeetupStatus, ParticipantStatus
from backend.app.db.models.meetup import Meetup
from backend.app.db.repositories import games as game_repository
from backend.app.db.repositories import meetups as meetup_repository
from backend.app.db.repositories import users as user_repository
from backend.app.schemas.meetup import (
    MeetupCreateRequest,
    MeetupGameSuggestionRead,
    MeetupGameVoterRead,
    MeetupGameVoteSummaryRead,
    MeetupParticipantRead,
    MeetupProposalSourceRead,
    MeetupRead,
    MeetupUpdateRequest,
)


class MeetupNotFoundError(ValueError):
    """Raised when a meetup does not exist."""


class MeetupForbiddenError(ValueError):
    """Raised when a user is not allowed to perform an action on a meetup."""


class MeetupCapacityFullError(ValueError):
    """Raised when a meetup has no free participant slots."""


class MeetupInvalidUpdateError(ValueError):
    """Raised when a meetup update violates its current constraints."""


class MeetupNotJoinableError(ValueError):
    """Raised when a meetup cannot accept new participants."""


class MeetupAlreadyJoinedError(ValueError):
    """Raised when a user is already a joined participant."""


class MeetupSuggestionNotAllowedError(ValueError):
    """Raised when a suggestion is outside the meetup or collection rules."""


class MeetupVoteNotAllowedError(ValueError):
    """Raised when a vote is outside the meetup's open game suggestions."""


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
    games = [
        game
        for meetup_game in meetup.meetup_games
        if (game := meetup_game.game) is not None
    ]
    proposal_sources = []
    creator = meetup.creator
    if any(user_game.game.game_type == GameType.BASE for user_game in creator.user_games):
        proposal_sources.append(
            MeetupProposalSourceRead(
                user_id=creator.id,
                display_name=creator.display_name,
                username=creator.username,
            )
        )
    for participant in sorted(
        meetup.participants,
        key=lambda entry: (entry.user.display_name.casefold(), entry.user.id),
    ):
        user = participant.user
        if (
            participant.status == ParticipantStatus.JOINED
            and user.id != meetup.creator_user_id
            and any(user_game.game.game_type == GameType.BASE for user_game in user.user_games)
        ):
            proposal_sources.append(
                MeetupProposalSourceRead(
                    user_id=user.id,
                    display_name=user.display_name,
                    username=user.username,
                )
            )

    suggestions_by_proposer: dict[int, MeetupGameSuggestionRead] = {}
    for suggestion in sorted(meetup.game_suggestions, key=lambda entry: entry.id):
        proposer = suggestion.proposer
        grouped = suggestions_by_proposer.get(proposer.id)
        if grouped is None:
            grouped = MeetupGameSuggestionRead(
                proposer_user_id=proposer.id,
                display_name=proposer.display_name,
                username=proposer.username,
                games=[],
            )
            suggestions_by_proposer[proposer.id] = grouped
        grouped.games.append(suggestion.game)

    votes_by_game: dict[int, MeetupGameVoteSummaryRead] = {}
    for suggestion in sorted(meetup.game_suggestions, key=lambda entry: entry.id):
        game = suggestion.game
        if game is not None:
            votes_by_game.setdefault(
                game.id,
                MeetupGameVoteSummaryRead(game_id=game.id),
            )
    for vote in meetup.game_votes:
        summary = votes_by_game.get(vote.game_id)
        if summary is not None:
            summary.voters.append(
                MeetupGameVoterRead(
                    user_id=vote.user.id,
                    display_name=vote.user.display_name,
                    username=vote.user.username,
                )
            )
    for summary in votes_by_game.values():
        summary.voters.sort(key=lambda voter: (voter.display_name.casefold(), voter.user_id))

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
        games=games,
        proposal_sources=proposal_sources,
        game_suggestions=list(suggestions_by_proposer.values()),
        game_suggestion_votes=list(votes_by_game.values()),
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
        title=payload.title,
        comment=payload.comment,
        telegram_chat_id=payload.telegram_chat_id,
        telegram_thread_id=payload.telegram_thread_id,
        location="",
        game_ids=payload.game_ids,
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
    archive: bool = False,
    telegram_chat_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[MeetupRead]:
    meetups = meetup_repository.list_meetups(
        db,
        archive=archive,
        telegram_chat_id=telegram_chat_id,
        limit=limit,
        offset=offset,
    )
    return [_build_meetup_read(meetup) for meetup in meetups]


def update_meetup(
    db: Session,
    meetup_id: int,
    payload: MeetupUpdateRequest,
) -> MeetupRead:
    meetup = meetup_repository.get_meetup_for_update(db, meetup_id)
    if meetup is None:
        raise MeetupNotFoundError("Meetup not found.")
    if meetup.creator_user_id != payload.requesting_user_id:
        raise MeetupForbiddenError("Only the meetup creator can edit it.")

    fields = payload.model_dump(
        exclude_unset=True,
        exclude={"requesting_user_id", "game_ids"},
    )
    if any(
        fields.get(field) is None
        for field in ("scheduled_at", "capacity_total")
        if field in fields
    ):
        raise MeetupInvalidUpdateError("Date and capacity cannot be cleared.")

    game_ids = payload.game_ids
    if game_ids is not None:
        unique_game_ids = list(dict.fromkeys(game_ids))
        if any(game_repository.get_game_by_id(db, game_id) is None for game_id in unique_game_ids):
            raise MeetupInvalidUpdateError("One or more selected games do not exist.")
        game_ids = unique_game_ids

    if "capacity_total" in fields:
        joined_count = meetup_repository.count_joined_participants(db, meetup_id)
        if fields["capacity_total"] < joined_count:
            raise MeetupInvalidUpdateError(
                "Capacity cannot be lower than the number of joined participants."
            )

    updated = meetup_repository.update_meetup(
        db,
        meetup,
        fields=fields,
        game_ids=game_ids,
    )
    return _build_meetup_read(updated)


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


def suggest_meetup_games(
    db: Session,
    *,
    meetup_id: int,
    proposer_user_id: int,
    collection_owner_user_id: int,
    game_ids: list[int],
) -> MeetupRead:
    meetup = meetup_repository.get_meetup_by_id(db, meetup_id)
    if meetup is None:
        raise MeetupNotFoundError("Meetup not found.")
    if meetup.status != MeetupStatus.PLANNED:
        raise MeetupSuggestionNotAllowedError("Meetup is not open for game suggestions.")

    proposer = user_repository.get_user_by_id(db, proposer_user_id)
    collection_owner = user_repository.get_user_by_id(db, collection_owner_user_id)
    if proposer is None or collection_owner is None:
        raise MeetupNotFoundError("User not found.")

    if collection_owner_user_id != proposer_user_id:
        is_meetup_collection = collection_owner_user_id == meetup.creator_user_id or any(
            participant.user_id == collection_owner_user_id
            and participant.status == ParticipantStatus.JOINED
            for participant in meetup.participants
        )
        if not is_meetup_collection:
            raise MeetupSuggestionNotAllowedError(
                "The selected collection does not belong to a meetup participant."
            )

    unique_game_ids = list(dict.fromkeys(game_ids))
    owned_game_ids = game_repository.list_owned_game_ids(
        db,
        user_id=collection_owner_user_id,
        game_ids=unique_game_ids,
    )
    if len(owned_game_ids) != len(unique_game_ids):
        raise MeetupSuggestionNotAllowedError(
            "One or more selected games are not in the selected collection."
        )

    meetup_repository.replace_game_suggestions(
        db,
        meetup_id=meetup_id,
        proposer_user_id=proposer_user_id,
        collection_owner_user_id=collection_owner_user_id,
        game_ids=unique_game_ids,
    )
    refreshed = meetup_repository.get_meetup_by_id(db, meetup_id)
    if refreshed is None:
        raise MeetupNotFoundError("Meetup not found.")
    return _build_meetup_read(refreshed)


def toggle_meetup_game_vote(
    db: Session,
    *,
    meetup_id: int,
    user_id: int,
    game_id: int,
) -> MeetupRead:
    meetup = meetup_repository.get_meetup_for_update(db, meetup_id)
    if meetup is None:
        raise MeetupNotFoundError("Meetup not found.")
    if meetup.status != MeetupStatus.PLANNED:
        raise MeetupVoteNotAllowedError("Meetup is not open for voting.")
    if not meetup_repository.has_suggested_game(db, meetup_id=meetup_id, game_id=game_id):
        raise MeetupVoteNotAllowedError("The game has not been suggested for this meetup.")
    if user_repository.get_user_by_id(db, user_id) is None:
        raise MeetupNotFoundError("User not found.")

    meetup_repository.toggle_game_vote(
        db,
        meetup_id=meetup_id,
        game_id=game_id,
        user_id=user_id,
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
