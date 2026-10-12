from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.schemas.game import GameRead


class GameRandomizerOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    value: str


class GameRandomizerCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    name: str
    draw_count: int | None
    options: list[GameRandomizerOptionRead]


class GameRandomizerGameRead(BaseModel):
    game: GameRead
    categories: list[GameRandomizerCategoryRead]


class GameRandomizerCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    draw_count: int | None = Field(default=None, ge=1, le=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Category name cannot be empty.")
        return value


class GameRandomizerCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    draw_count: int | None = Field(default=None, ge=1, le=100)
    update_draw_count: bool = False

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Category name cannot be empty.")
        return value

    @model_validator(mode="after")
    def has_an_update(self) -> "GameRandomizerCategoryUpdate":
        if self.name is None and not self.update_draw_count:
            raise ValueError("At least one category property must be updated.")
        return self


class GameRandomizerOptionsCreate(BaseModel):
    values: list[str] = Field(min_length=1, max_length=100)

    @field_validator("values")
    @classmethod
    def clean_values(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("Options cannot be empty.")
        if any(len(value) > 500 for value in cleaned):
            raise ValueError("Options cannot exceed 500 characters.")
        return cleaned


class GameRandomizerOptionUpdate(BaseModel):
    value: str = Field(min_length=1, max_length=500)

    @field_validator("value")
    @classmethod
    def strip_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Option cannot be empty.")
        return value


class GameRandomizerDrawRequest(BaseModel):
    category_ids: list[int] = Field(min_length=1, max_length=50)
    player_count: int | None = Field(default=None, ge=1, le=100)


class GameRandomizerDrawCategory(BaseModel):
    category_id: int
    category_name: str
    requested_count: int
    available_count: int
    selected: list[str]
    shortage: int


class GameRandomizerDrawRead(BaseModel):
    game: GameRead
    categories: list[GameRandomizerDrawCategory]
