from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.models.enums import MeetupStatus, ParticipantStatus


class MeetupCreateRequest(BaseModel):
    creator_user_id: int = Field(..., ge=1)
    scheduled_at: datetime
    capacity_total: int = Field(..., ge=1)
    comment: str | None = Field(default=None, max_length=4000)
    telegram_chat_id: int | None = Field(default=None)
    telegram_thread_id: int | None = Field(default=None)


class MeetupJoinRequest(BaseModel):
    user_id: int = Field(..., ge=1)


class MeetupLeaveRequest(BaseModel):
    user_id: int = Field(..., ge=1)


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
