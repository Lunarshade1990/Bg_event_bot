from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.models.enums import ImportJobStatus


class BggCollectionImportRequest(BaseModel):
    telegram_id: int = Field(..., ge=1)
    bgg_username: str | None = Field(default=None, min_length=1, max_length=255)


class BggCollectionImportResult(BaseModel):
    job_id: int
    user_id: int
    bgg_username: str
    status: ImportJobStatus
    collection_games_count: int
    processed_games: int
    created_games: int
    updated_games: int
    linked_games: int


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    bgg_username: str
    status: ImportJobStatus
    imported_count: int
    error_message: str | None
