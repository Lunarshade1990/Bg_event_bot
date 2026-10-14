from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.models.enums import MeetupStatus, ParticipantStatus
from backend.app.schemas.game import GameRead


class MeetupCreateRequest(BaseModel):
    creator_user_id: int = Field(..., ge=1)
    scheduled_at: datetime
    capacity_total: int = Field(..., ge=1)
    comment: str | None = Field(default=None, max_length=4000)
    telegram_chat_id: int | None = Field(default=None)
    telegram_thread_id: int | None = Field(default=None)
    game_ids: list[int] = Field(default_factory=list)


class MeetupJoinRequest(BaseModel):
    user_id: int = Field(..., ge=1)


class MeetupLeaveRequest(BaseModel):
    user_id: int = Field(..., ge=1)


class MeetupGameSuggestionRequest(BaseModel):
    proposer_user_id: int = Field(..., ge=1)
    collection_owner_user_id: int = Field(..., ge=1)
    game_ids: list[int] = Field(..., min_length=1)


class MeetupGameVoteRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    game_id: int = Field(..., ge=1)


class MeetupTelegramMessageRequest(BaseModel):
    telegram_message_id: int = Field(..., ge=1)


class MeetupDeleteRequest(BaseModel):
    requesting_user_id: int = Field(..., ge=1)


class MeetupParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    display_name: str
    username: str | None
    status: ParticipantStatus


class MeetupProposalSourceRead(BaseModel):
    user_id: int
    display_name: str
    username: str | None


class MeetupGameSuggestionRead(BaseModel):
    proposer_user_id: int
    display_name: str
    username: str | None
    games: list[GameRead]


class MeetupGameVoterRead(BaseModel):
    user_id: int
    display_name: str
    username: str | None


class MeetupGameVoteSummaryRead(BaseModel):
    game_id: int
    voters: list[MeetupGameVoterRead] = Field(default_factory=list)


class MeetupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduled_at: datetime
    capacity_total: int
    comment: str | None
    status: MeetupStatus
    creator_user_id: int
    telegram_chat_id: int | None
    telegram_thread_id: int | None
    telegram_message_id: int | None
    participants: list[MeetupParticipantRead]
    games: list[GameRead] = Field(default_factory=list)
    proposal_sources: list[MeetupProposalSourceRead] = Field(default_factory=list)
    game_suggestions: list[MeetupGameSuggestionRead] = Field(default_factory=list)
    game_suggestion_votes: list[MeetupGameVoteSummaryRead] = Field(default_factory=list)
