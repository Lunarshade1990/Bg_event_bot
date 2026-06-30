from pydantic import BaseModel, ConfigDict, Field


class UserTelegramSyncRequest(BaseModel):
    telegram_id: int = Field(..., ge=1)
    username: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    bgg_username: str | None = Field(default=None, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    display_name: str
    bgg_username: str | None
    is_admin: bool
    is_active: bool


class UserSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None
    display_name: str
    bgg_username: str | None
