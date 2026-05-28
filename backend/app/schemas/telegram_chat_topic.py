from pydantic import BaseModel, ConfigDict, Field


class TelegramChatTopicCreateRequest(BaseModel):
    telegram_chat_id: int
    telegram_thread_id: int = Field(..., ge=1)
    title: str | None = Field(default=None, max_length=255)


class TelegramChatMembershipCreateRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    telegram_chat_id: int
    telegram_thread_id: int = Field(..., ge=1)
    title: str | None = Field(default=None, max_length=255)


class TelegramChatTopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_chat_id: int
    telegram_thread_id: int
    title: str | None
