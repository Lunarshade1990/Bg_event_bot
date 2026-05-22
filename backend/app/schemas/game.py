from pydantic import BaseModel, ConfigDict

from backend.app.db.models.enums import CampaignSource, GameType


class GameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bgg_id: int
    title: str
    original_title: str | None
    author: str | None
    min_players: int
    max_players: int
    play_time_minutes: int | None
    image_url: str | None
    game_type: GameType
    has_campaign: bool
    campaign_source: CampaignSource


class GameOwnerRead(BaseModel):
    user_id: int
    display_name: str
    username: str | None
    bgg_username: str | None
    is_available_for_meetups: bool
    comment: str | None
